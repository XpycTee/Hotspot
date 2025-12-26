from core.logging import get_logger

from pyrad2 import packet


logger = get_logger('radius.hotpsot.packet')

class BasePacket(packet.Packet):
    def debug_log_attributes(self):
        logger.debug('Attributes:')
        for attr in self.keys():
            logger.debug(f'{attr}: {self[attr]}')

    def get_attribute(self, key, default=None):
        return self.get(key, [default])[0]


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