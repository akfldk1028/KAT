import React, { useEffect, useState } from 'react';
import styled from 'styled-components';

const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 2000;
`;

const ImageContainer = styled.div`
  position: relative;
  max-width: 90%;
  max-height: 80%;
  display: flex;
  justify-content: center;
  align-items: center;
`;

const StyledImage = styled.img`
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
`;

const ButtonContainer = styled.div`
  display: flex;
  gap: 16px;
  margin-top: 24px;
`;

const Button = styled.button<{ variant?: 'primary' | 'secondary' }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  ${({ variant }) => variant === 'primary' ? `
    background: #ffeb33;
    color: #000;
    &:hover {
      background: #ffe000;
    }
  ` : `
    background: rgba(255, 255, 255, 0.2);
    color: white;
    &:hover {
      background: rgba(255, 255, 255, 0.3);
    }
  `}
`;

const CloseButton = styled.button`
  position: absolute;
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.3);
  }
`;

const LoadingText = styled.div`
  color: white;
  font-size: 16px;
`;

interface Props {
  imageUrl: string;
  onClose: () => void;
}

const ImageViewerModal: React.FC<Props> = ({ imageUrl, onClose }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleDownload = async () => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // 파일명 추출 또는 기본값
      const filename = imageUrl.split('/').pop() || `image_${Date.now()}.jpg`;
      link.download = filename;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
      // fallback: 새 창에서 열기
      window.open(imageUrl, '_blank');
    }
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <Overlay onClick={handleOverlayClick}>
      <CloseButton onClick={onClose}>×</CloseButton>

      <ImageContainer>
        {isLoading && <LoadingText>이미지 로딩 중...</LoadingText>}
        {error ? (
          <LoadingText>이미지를 불러올 수 없습니다</LoadingText>
        ) : (
          <StyledImage
            src={imageUrl}
            alt="확대된 이미지"
            onLoad={() => setIsLoading(false)}
            onError={() => {
              setIsLoading(false);
              setError(true);
            }}
            style={{ display: isLoading ? 'none' : 'block' }}
          />
        )}
      </ImageContainer>

      <ButtonContainer>
        <Button variant="primary" onClick={handleDownload}>
          <DownloadIcon />
          다운로드
        </Button>
        <Button onClick={onClose}>
          닫기
        </Button>
      </ButtonContainer>
    </Overlay>
  );
};

// 다운로드 아이콘 SVG
const DownloadIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7,10 12,15 17,10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

export default ImageViewerModal;
