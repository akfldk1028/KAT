import React, { useState } from 'react';
import styled from 'styled-components';
import { IconButton } from '~/components/common';
import { PlusIcon, EmojiIcon } from './Icons';
import ImageUploadButton from './ImageUploadButton';
import MessageInput from './MessageInput';
import SendButton from './SendButton';

const Wrapper = styled.footer`
  position: fixed;
  bottom: 0px;
  left: 0px;
  right: 0px;
  width: 100%;
  min-height: 56px;
  padding: 8px 12px;
  z-index: 100;
  background-color: #f5f5f5;
  border-top: 1px solid #e0e0e0;
`;

const InputRow = styled.div`
  display: flex;
  align-items: flex-end;
  gap: 8px;
`;

const LeftButtons = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
`;

interface Props {
  onChatSumbmit: (msg: string) => void;
  onImageSelect?: (file: File) => void;
}

const Footer: React.FC<Props> = ({ onChatSumbmit, onImageSelect }) => {
  const [message, setMessage] = useState('');

  const isCanSubmit = !!message.replace(/ |\n/g, '');

  const handleSubmit = () => {
    if (isCanSubmit) {
      onChatSumbmit(message);
      setMessage('');
    }
  };

  const handleImageSelect = (file: File) => {
    if (onImageSelect) {
      onImageSelect(file);
    }
  };

  return (
    <Wrapper>
      <InputRow>
        <LeftButtons>
          <IconButton icon={<PlusIcon />} title="더보기" />
          <ImageUploadButton onImageSelect={handleImageSelect} />
          <IconButton icon={<EmojiIcon />} title="이모티콘" />
        </LeftButtons>

        <MessageInput
          value={message}
          onChange={setMessage}
          onSubmit={handleSubmit}
        />

        <SendButton isActive={isCanSubmit} onClick={handleSubmit} />
      </InputRow>
    </Wrapper>
  );
};

export default Footer;
