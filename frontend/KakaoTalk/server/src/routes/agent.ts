/**
 * Agent API Routes
 * FastAPI Agent 서버로 프록시
 */
import * as express from 'express';
import multer from 'multer';
import * as path from 'path';
import { analyzeOutgoing, analyzeIncoming, analyzeImage, checkAgentHealth } from '../services/agentService';
import * as fs from 'fs';

const router = express.Router();

// 임시 파일 저장 경로
const dest = path.join(__dirname, '../uploads/temp/');

// 디렉토리가 없으면 생성
if (!fs.existsSync(dest)) {
  fs.mkdirSync(dest, { recursive: true });
}

const upload = multer({ dest });

/**
 * 헬스체크
 */
router.get('/health', async (req, res) => {
  const isHealthy = await checkAgentHealth();
  if (isHealthy) {
    return res.json({ status: 'ok', service: 'DualGuard Agent Proxy' });
  }
  return res.status(503).json({ status: 'error', message: 'Agent API unavailable' });
});

/**
 * 발신 메시지 분석
 */
router.post('/analyze/outgoing', async (req, res) => {
  try {
    const { text, sender_id, receiver_id } = req.body;
    const result = await analyzeOutgoing(text, sender_id, receiver_id);

    if (result) {
      return res.json(result);
    }

    // Agent API 실패 시 기본 응답
    return res.json({
      risk_level: 'LOW',
      reasons: ['분석 서버 연결 실패'],
      recommended_action: '서버 연결을 확인하세요',
      is_secret_recommended: false
    });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

/**
 * 수신 메시지 분석
 */
router.post('/analyze/incoming', async (req, res) => {
  try {
    const { text, sender_id, receiver_id, use_ai } = req.body;
    const result = await analyzeIncoming(text, sender_id, receiver_id);

    if (result) {
      return res.json(result);
    }

    return res.json({
      risk_level: 'LOW',
      reasons: ['분석 서버 연결 실패'],
      recommended_action: '서버 연결을 확인하세요',
      is_secret_recommended: false
    });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

/**
 * 이미지 분석
 */
router.post('/analyze/image', upload.single('file'), async (req, res) => {
  let tempFilePath: string | null = null;

  try {
    const file = req.file as Express.Multer.File;
    if (!file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    tempFilePath = file.path;

    // 파일 버퍼 읽기
    const fileBuffer = fs.readFileSync(file.path);
    const result = await analyzeImage(fileBuffer, file.originalname);

    if (result) {
      return res.json(result);
    }

    return res.json({
      risk_level: 'LOW',
      reasons: ['분석 서버 연결 실패'],
      recommended_action: '서버 연결을 확인하세요',
      is_secret_recommended: false
    });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  } finally {
    // 임시 파일 정리
    if (tempFilePath && fs.existsSync(tempFilePath)) {
      fs.unlinkSync(tempFilePath);
    }
  }
});

export default router;
