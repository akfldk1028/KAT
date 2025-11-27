import React, { useRef, ChangeEvent, KeyboardEvent } from 'react';
import styled from 'styled-components';

const Wrapper = styled.div`
  flex: 1;
  display: flex;
  align-items: flex-end;
  background: white;
  border-radius: 20px;
  border: 1px solid #ddd;
  padding: 8px 16px;
  min-height: 40px;
  max-height: 120px;
`;

const TextArea = styled.textarea`
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.4;
  max-height: 100px;
  overflow-y: auto;
  background: transparent;

  &::placeholder {
    color: #999;
  }
`;

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
}

const MessageInput: React.FC<Props> = ({
  value,
  onChange,
  onSubmit,
  placeholder = '메시지 입력'
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = event.target.value;
    onChange(newValue);

    // 자동 높이 조절
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 100)}px`;
    }
  };

  const handleKeyPress = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Shift + Enter = 줄바꿈, Enter = 전송
    if (!event.shiftKey && event.key === 'Enter') {
      event.preventDefault();
      onSubmit();

      // 높이 초기화
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  return (
    <Wrapper>
      <TextArea
        ref={textareaRef}
        value={value}
        placeholder={placeholder}
        onChange={handleChange}
        onKeyPress={handleKeyPress}
        rows={1}
      />
    </Wrapper>
  );
};

export default MessageInput;
