from radius.logging import logger


from pyrad2 import packet
from pyrad2.constants import PacketType


class BasePacket(packet.Packet):
    def debug_log_attributes(self):
        logger.debug('Attributes:')
        for attr in self.keys():
            logger.debug(f'{attr}: {self[attr]}')

    def get_attribute(self, key, default=None):
        return self.get(key, [default])[0]

    def create_reply(self, **attributes):
        return super().CreateReply(**attributes)

    def reply_accept(self, is_employee):
        reply = self.create_reply()
        reply.AddAttribute('MT-Group', 'employee' if is_employee else 'guest')
        reply.code = PacketType.AccessAccept
        return reply

    def reply_reject(self, error_message: str, log_=logger.info):
        reply = self.create_reply()
        reply.AddAttribute('Reply-Message', error_message)
        reply.code = PacketType.AccessReject

        log_(error_message)

        return reply


class HotspotAuthPacket(BasePacket, packet.AuthPacket):
    def verify_password(self, password: str):
        if 'User-Password' in self:
            encrypted_user_password = self.get_attribute('User-Password')
            user_password = self.PwDecrypt(encrypted_user_password)
            auth_success = user_password == password
        elif 'CHAP-Password' in self:
            auth_success = self.VerifyChapPasswd(password)
        else:
            auth_success = False
            logger.warning('No password attribute')
        return auth_success


class HotspotAcctPacket(BasePacket, packet.AcctPacket):
    pass