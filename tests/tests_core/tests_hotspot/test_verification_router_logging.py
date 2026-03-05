import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.hotspot.verification.api import DeliveryStatus, SendCodeResult
from core.hotspot.verification.router import VRouterStatus, VerificationRouter
from core.config.models.verificators import VProviderType, VerificationMethod


def _provider_cfg(vtype: VProviderType, methods: list[VerificationMethod], enabled=True):
    return SimpleNamespace(
        type=vtype,
        enabled=enabled,
        supported_methods=methods,
        fields=[SimpleNamespace(value='dummy')],
    )


class TestVerificationRouterLogging(unittest.TestCase):
    @patch('core.hotspot.verification.router.logger.warning')
    @patch('core.hotspot.verification.router.logger.info')
    @patch('core.hotspot.verification.router.HuaweiSMSSender')
    @patch('core.hotspot.verification.router.DebugCodeDelivery')
    @patch('core.hotspot.verification.router.get_config')
    def test_send_code_logs_fallback_and_success(
        self,
        mock_get_config,
        mock_debug_sender_cls,
        mock_huawei_sender_cls,
        mock_logger_info,
        mock_logger_warning,
    ):
        config = SimpleNamespace(
            verificators=SimpleNamespace(
                items=[
                    _provider_cfg(VProviderType.DEBUG, [VerificationMethod.CODE]),
                    _provider_cfg(VProviderType.HUAWEI, [VerificationMethod.CODE]),
                ],
                order=[VProviderType.DEBUG, VProviderType.HUAWEI],
            )
        )
        mock_get_config.return_value = config

        debug_sender = MagicMock()
        debug_sender.send_code.return_value = SendCodeResult(
            status=DeliveryStatus.ERROR,
            error_message='debug err',
        )
        huawei_sender = MagicMock()
        huawei_sender.send_code.return_value = SendCodeResult(
            status=DeliveryStatus.SENT,
        )
        mock_debug_sender_cls.return_value = debug_sender
        mock_huawei_sender_cls.return_value = huawei_sender

        router = VerificationRouter(flow_ctx={'auth_flow_id': 'flow-1', 'verify_session_id': 'verify-1', 'stage': 'code.send'})
        result = router.send_code('79990000000', '1234')

        self.assertEqual(result.status, VRouterStatus.SENDED)
        self.assertEqual(result.provider, VProviderType.HUAWEI)

        warning_extras = [kwargs.get('extra', {}) for _, kwargs in mock_logger_warning.call_args_list]
        self.assertTrue(any(extra.get('operation') == 'send_code' for extra in warning_extras))
        self.assertTrue(any(extra.get('provider') == 'DEBUG' for extra in warning_extras))

        info_extras = [kwargs.get('extra', {}) for _, kwargs in mock_logger_info.call_args_list]
        self.assertTrue(any(extra.get('provider') == 'HUAWEI' for extra in info_extras))

    @patch('core.hotspot.verification.router.logger.error')
    @patch('core.hotspot.verification.router.HuaweiSMSSender')
    @patch('core.hotspot.verification.router.get_config')
    def test_send_code_logs_provider_on_exhausted(self, mock_get_config, mock_huawei_sender_cls, mock_logger_error):
        config = SimpleNamespace(
            verificators=SimpleNamespace(
                items=[_provider_cfg(VProviderType.HUAWEI, [VerificationMethod.CODE])],
                order=[VProviderType.HUAWEI],
            )
        )
        mock_get_config.return_value = config

        sender = MagicMock()
        sender.send_code.return_value = SendCodeResult(
            status=DeliveryStatus.ERROR,
            error_message='huawei err',
        )
        mock_huawei_sender_cls.return_value = sender

        router = VerificationRouter(flow_ctx={'auth_flow_id': 'flow-1', 'verify_session_id': 'verify-1', 'stage': 'code.send'})
        result = router.send_code('79990000000', '1234')

        self.assertEqual(result.status, VRouterStatus.ERROR)
        self.assertEqual(result.provider, VProviderType.HUAWEI)
        self.assertEqual(result.error_message, 'huawei err')

        self.assertTrue(mock_logger_error.called)
        _, kwargs = mock_logger_error.call_args
        self.assertEqual(kwargs.get('extra', {}).get('operation'), 'send_code')
