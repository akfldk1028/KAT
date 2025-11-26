/**
 * Node.js → FastAPI 통신 테스트
 * agentService를 통한 Agent API 호출 검증
 */

const axios = require('axios');

const AGENT_API_BASE_URL = 'http://localhost:8000/api/agents';

async function testAgentService() {
    console.log('='.repeat(60));
    console.log('🔗 Node.js → FastAPI Agent Service 통신 테스트');
    console.log('='.repeat(60));

    const testCases = [
        {
            name: 'Outgoing Agent - 계좌번호 감지',
            endpoint: '/analyze/outgoing',
            data: { text: '계좌번호 123-45-67890 이거야' },
            expected: 'MEDIUM'
        },
        {
            name: 'Outgoing Agent - 일반 메시지',
            endpoint: '/analyze/outgoing',
            data: { text: '오늘 점심 뭐 먹을래?' },
            expected: 'LOW'
        },
        {
            name: 'Incoming Agent - 가족 사칭',
            endpoint: '/analyze/incoming',
            data: { text: '엄마 나야. 폰 고장났어. 급해서 돈 좀 보내줘' },
            expected: 'CRITICAL'
        },
        {
            name: 'Incoming Agent - 일반 메시지',
            endpoint: '/analyze/incoming',
            data: { text: '오늘 날씨 좋네' },
            expected: 'LOW'
        }
    ];

    let passed = 0;
    let failed = 0;

    for (const test of testCases) {
        console.log(`\n[테스트] ${test.name}`);
        console.log(`메시지: ${test.data.text}`);

        try {
            const response = await axios.post(
                `${AGENT_API_BASE_URL}${test.endpoint}`,
                test.data,
                {
                    timeout: 5000,
                    headers: { 'Content-Type': 'application/json' }
                }
            );

            const result = response.data;
            const success = result.risk_level === test.expected;

            if (success) {
                console.log(`✅ 통과: 위험도 ${result.risk_level} (예상: ${test.expected})`);
                console.log(`   이유: ${result.reasons.join(', ') || '없음'}`);
                passed++;
            } else {
                console.log(`❌ 실패: 위험도 ${result.risk_level} (예상: ${test.expected})`);
                failed++;
            }

        } catch (error) {
            console.log(`❌ 오류: ${error.message}`);
            failed++;
        }
    }

    console.log('\n' + '='.repeat(60));
    console.log(`📊 테스트 결과: ${passed}/${testCases.length} 통과`);
    console.log('='.repeat(60));

    if (failed === 0) {
        console.log('✅ 모든 테스트 통과! Node.js ↔ FastAPI 통신 정상');
        process.exit(0);
    } else {
        console.log(`⚠️  ${failed}개 테스트 실패`);
        process.exit(1);
    }
}

// 실행
testAgentService().catch(error => {
    console.error('테스트 실행 오류:', error);
    process.exit(1);
});
