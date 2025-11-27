import React, { useRef, ChangeEvent } from 'react';
import styled from 'styled-components';
import { ImageIcon } from './Icons';

const Label = styled.label`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  & input {
    display: none;
  }

  & svg {
    width: 24px;
    height: 24px;
    fill: #666;
  }
`;

const VALID_IMAGE_TYPES = [
  'image/png',
  'image/jpg',
  'image/jpeg',
  'image/bmp',
  'image/gif'
];

interface Props {
  onImageSelect: (file: File) => void;
}

const ImageUploadButton: React.FC<Props> = ({ onImageSelect }) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    event.preventDefault();

    const file = event.target.files?.[0];
    if (!file) return;

    if (VALID_IMAGE_TYPES.includes(file.type)) {
      onImageSelect(file);
    } else {
      alert('이미지 파일만 선택할 수 있습니다.');
    }

    // 같은 파일 재선택 가능하도록 초기화
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <Label title="사진">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleChange}
      />
      <ImageIcon />
    </Label>
  );
};

export default ImageUploadButton;
