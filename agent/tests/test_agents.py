"""
Agent 단위 테스트
"""
import unittest
from ..core.models import RiskLevel
from ..agents.outgoing import OutgoingAgent
from ..agents.incoming import IncomingAgent


class TestOutgoingAgent(unittest.TestCase):
    """안심 전송 Agent 테스트"""

    def setUp(self):
        self.agent = OutgoingAgent()

    def test_account_number_detection(self):
        """계좌번호 감지 테스트"""
        result = self.agent.analyze("내 계좌번호는 110-123-456789이야")
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertTrue(result.is_secret_recommended)
        self.assertIn("계좌번호", result.reasons[0])

    def test_resident_id_detection(self):
        """주민등록번호 감지 테스트"""
        result = self.agent.analyze("주민번호 900101-1234567 보내줄게")
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertTrue(result.is_secret_recommended)
        self.assertIn("주민등록번호", result.reasons[0])

    def test_phone_number_detection(self):
        """전화번호 감지 테스트"""
        result = self.agent.analyze("연락처는 010-1234-5678이야")
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertFalse(result.is_secret_recommended)

    def test_card_number_detection(self):
        """신용카드번호 감지 테스트"""
        result = self.agent.analyze("카드번호 1234-5678-9012-3456")
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertTrue(result.is_secret_recommended)

    def test_clean_message(self):
        """민감정보 없는 메시지 테스트"""
        result = self.agent.analyze("안녕하세요 오늘 날씨 좋네요")
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertFalse(result.is_secret_recommended)
        self.assertEqual(len(result.reasons), 0)

    def test_multiple_pii_detection(self):
        """복합 민감정보 감지 테스트"""
        result = self.agent.analyze("계좌 110-123-456789, 주민번호 900101-1234567")
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertTrue(result.is_secret_recommended)
        self.assertEqual(len(result.reasons), 2)


class TestIncomingAgent(unittest.TestCase):
    """안심 가드 Agent 테스트"""

    def setUp(self):
        self.agent = IncomingAgent()

    def test_family_impersonation_critical(self):
        """가족 사칭 + 금전 요구 = CRITICAL"""
        result = self.agent.analyze("엄마 나야 폰 고장나서 새번호야 급해서 그러는데 돈 좀 보내줘")
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)
        self.assertIn("가족 사칭 및 금전 요구", result.reasons[0])

    def test_family_impersonation_medium(self):
        """가족 사칭만 = MEDIUM"""
        result = self.agent.analyze("엄마 나야 폰 고장나서 새번호야")
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("가족 사칭 의심", result.reasons[0])

    def test_urgent_request_medium(self):
        """긴급 요청만 = MEDIUM"""
        result = self.agent.analyze("급해서 그러는데 돈 좀 보내줘")
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("송금 유도", result.reasons[0])

    def test_phishing_link_detection(self):
        """피싱 링크 감지 테스트"""
        result = self.agent.analyze("여기서 확인하세요 http://kakao-verify.com/login")
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("링크", result.reasons[0])

    def test_clean_message(self):
        """정상 메시지 테스트"""
        result = self.agent.analyze("오늘 저녁에 만날까?")
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(len(result.reasons), 0)

    def test_short_url_detection(self):
        """단축 URL 감지 테스트"""
        result = self.agent.analyze("이 링크 확인해봐 bit.ly/abc123")
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)


def run_tests():
    """테스트 실행"""
    unittest.main(module=__name__, exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()
