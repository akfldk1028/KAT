import re

# Read the file
with open('D:/Data/18_KAT/KAT/frontend/KakaoTalk/client/src/containers/chattingRoom/ChattingRoomContainer.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Change onChatSubmit to analyze BEFORE sending
old_onChatSubmit = '''    const onChatSumbmit = async (msg: string) => {
      // 1. 먼저 메시지 전송 (낙관적 UI - 바로 채팅창에 표시)
      this.sendTextMessage(msg);

      // 2. 로딩 표시 + AI 분석 시작 (백그라운드)
      this.setState({ isAnalyzing: true, pendingTextMessage: msg });

      try {
        // Kanana LLM + MCP 도구로 분석 (use_ai: true)
        const analysis = await analyzeOutgoing(msg, true);

        // 3. 민감정보 감지 시 팝업 표시
        if (analysis.risk_level !== 'LOW' && analysis.is_secret_recommended) {
          this.setState({
            securityAnalysis: analysis,
            isTextAnalysis: true,
            isAnalyzing: false
          });
          // 팝업에서 사용자가 취소/확인 선택
        } else {
          // 분석 통과 - 로딩만 숨김
          this.setState({ isAnalyzing: false, pendingTextMessage: null });
        }
      } catch (error) {
        console.error('텍스트 분석 실패:', error);
        // 분석 실패 시 로딩만 숨김 (이미 전송됨)
        this.setState({ isAnalyzing: false, pendingTextMessage: null });
      }
    };'''

new_onChatSubmit = '''    const onChatSumbmit = async (msg: string) => {
      // 1. 먼저 AI 분석 (전송 전에!)
      this.setState({ isAnalyzing: true, pendingTextMessage: msg });

      try {
        // Kanana LLM + MCP 도구로 분석 (use_ai: true)
        const analysis = await analyzeOutgoing(msg, true);

        // 2. 민감정보 감지 시 팝업 표시 (메시지 아직 안 보냄)
        if (analysis.risk_level !== 'LOW' && analysis.is_secret_recommended) {
          this.setState({
            securityAnalysis: analysis,
            isTextAnalysis: true,
            isAnalyzing: false
          });
          // 팝업에서 사용자가 "그냥 보내기" 또는 "시크릿 전송" 선택
        } else {
          // 분석 통과 - 바로 메시지 전송
          this.sendTextMessage(msg);
          this.setState({ isAnalyzing: false, pendingTextMessage: null });
        }
      } catch (error) {
        console.error('텍스트 분석 실패:', error);
        // 분석 실패 시 그냥 전송 (안전하게)
        this.sendTextMessage(msg);
        this.setState({ isAnalyzing: false, pendingTextMessage: null });
      }
    };'''

content = content.replace(old_onChatSubmit, new_onChatSubmit)

# Fix 2: handleNormalSend should send the pending message
old_handleNormalSend = '''  // SecurityAlert에서 "그냥 보내기" 클릭 → 팝업 닫기 (이미 전송됨)
  handleNormalSend = () => {
    this.clearAnalysisState();
  };'''

new_handleNormalSend = '''  // SecurityAlert에서 "그냥 보내기" 클릭 → 일반 메시지로 전송
  handleNormalSend = () => {
    const { pendingTextMessage } = this.state;
    if (pendingTextMessage) {
      this.sendTextMessage(pendingTextMessage);
    }
    this.clearAnalysisState();
  };'''

content = content.replace(old_handleNormalSend, new_handleNormalSend)

# Write back
with open('D:/Data/18_KAT/KAT/frontend/KakaoTalk/client/src/containers/chattingRoom/ChattingRoomContainer.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('ChattingRoomContainer.tsx fixed!')
print('- onChatSubmit: now analyzes BEFORE sending')
print('- handleNormalSend: now sends pending message on "그냥 보내기"')
