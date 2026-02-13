from typing import Protocol

from core.config.models.verificators import SendCodeResult, StartVerificationResult, VerificationMethod, VerificationStatus
from core.logging import get_logger


logger = get_logger('core.hotspot.verification.api')


from typing import Protocol


class CodeDeliveryProvider(Protocol):
    """
    Interface for providers responsible for delivering one-time verification
    codes to end users.

    This provider type supports transport-level delivery mechanisms such as:

    - SMS (text message)
    - Voice message (text-to-speech call with code)
    - Flash call with embedded code
    - Other code-based delivery channels

    The provider is responsible strictly for message transport.
    It does NOT validate codes, manage verification sessions,
    enforce TTL, or implement retry policies.

    Business rules (rate limits, resend logic, attempt counters,
    lockouts, fallback strategies) must be implemented at the
    orchestration or application layer.

    Implementations should be stateless where possible and must
    tolerate network-level retries safely.
    """

    def send_code(self, phone: str, code: str, method: "VerificationMethod") -> "SendCodeResult":
        """
        Sends a one-time verification code to the specified phone number.

        Parameters
        ----------
        phone : str
            Target phone number in E.164 format.

        code : str
            Verification code to be delivered.
            The provider MUST treat this value as opaque and must not
            modify, generate, or validate it.

        method : VerificationMethod
            Desired delivery channel (e.g., SMS, VOICE, FLASH_CALL).
            The provider may reject unsupported methods explicitly.

        Returns
        -------
        SendCodeResult
            Structured result containing:
            - delivery status (SENT, FAILED, ERROR)
            - optional provider message identifier
            - optional diagnostic information

        Raises
        ------
        ProviderError
            If the provider API is unavailable or returns an unrecoverable error.

        Contract
        --------
        - This method must be non-blocking with respect to user interaction.
        - Successful return with status SENT indicates the provider
          has accepted the message for delivery, not that the user
          has received or read it.
        - The method must not perform verification or polling.

        Error Semantics
        ---------------
        FAILED → provider explicitly rejected the request
                 (e.g., invalid number, blocked destination).

        ERROR  → transient or technical failure
                 (e.g., network timeout, upstream service failure).

        Important
        ---------
        The provider MUST NOT implement retry loops internally unless
        explicitly required by the external API contract.
        Retry strategy is the responsibility of the orchestration layer.
        """



class CallConfirmationProvider(Protocol):
    """
    Interface for providers that implement call-based phone verification.

    This provider type supports verification flows where the user must
    confirm ownership of a phone number through a voice interaction.
    The exact mechanism may vary:

    - The provider calls the user automatically
    - The user must call a provider-issued number
    - The provider verifies the last digits of an incoming call
    - Any other call-based confirmation workflow

    The provider is responsible only for adapting the external API.
    Business logic such as polling limits, TTL enforcement, retries,
    and fallback handling must be implemented at the orchestration layer.

    All methods must be idempotent with respect to network retries
    whenever possible.
    """

    def start_verification(self, phone: str) -> "StartVerificationResult":
        """
        Initiates a call-based verification session.

        Parameters
        ----------
        phone : str
            Phone number in E.164 format.

        Returns
        -------
        StartVerificationResult
            Structured result containing:
            - request_id (unique verification session identifier)
            - action required from the client (e.g., WAIT_CALL, CALL_NUMBER)
            - optional metadata (e.g., number to call, TTL)

        Raises
        ------
        ProviderError
            If the provider API is unavailable or returns an unrecoverable error.

        Notes
        -----
        - This method MUST NOT block waiting for verification completion.
        - It only initiates the verification process.
        - The returned request_id must be suitable for subsequent
          calls to `check_verification`.
        """

    def check_verification(self, request_id: str) -> "VerificationStatus":
        """
        Checks the current state of a previously started verification session.

        Parameters
        ----------
        request_id : str
            Identifier returned by `start_verification`.

        Returns
        -------
        VerificationStatus
            One of:
            - PENDING   → verification still in progress
            - VERIFIED  → verification successfully completed
            - FAILED    → verification definitively rejected
            - EXPIRED   → verification window expired
            - ERROR     → technical failure occurred

        Contract
        --------
        - This method must be safe to call multiple times (polling scenario).
        - It must not mutate provider state beyond what is required
          to reflect the remote system's state.
        - Temporary network errors should be mapped to ERROR,
          not FAILED.

        Important
        ---------
        The provider MUST NOT implement retry loops or polling internally.
        Polling strategy and timeout handling are the responsibility
        of the orchestration layer.
        """