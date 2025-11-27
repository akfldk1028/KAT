import React from 'react';
import styled from 'styled-components';

const Wrapper = styled.div`
  margin-bottom: 16px;
  border-radius: 8px;
  overflow: hidden;
  max-height: 200px;

  & img {
    width: 100%;
    height: auto;
    object-fit: cover;
  }
`;

interface Props {
  src: string;
  alt?: string;
}

const ImagePreview: React.FC<Props> = ({ src, alt = '분석된 이미지' }) => {
  return (
    <Wrapper>
      <img src={src} alt={alt} />
    </Wrapper>
  );
};

export default ImagePreview;
