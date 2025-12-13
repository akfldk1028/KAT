import React from 'react';
import styled from 'styled-components';

const List = styled.ul`
  margin: 0 0 16px 0;
  padding: 0 0 0 20px;

  & li {
    margin-bottom: 8px;
    color: #666;
    font-size: 14px;
    line-height: 1.5;
  }
`;

interface Props {
  reasons: string[];
}

const ReasonList: React.FC<Props> = ({ reasons }) => {
  if (reasons.length === 0) {
    return null;
  }

  // 중복 제거 및 유효한 항목만 필터링
  const seen = new Set<string>();
  const uniqueReasons: string[] = [];

  for (const reason of reasons) {
    // 빈 문자열 필터링
    if (!reason || !reason.trim()) {
      continue;
    }
    // JSON 형태 데이터 필터링
    if (reason.includes('"name"') || reason.includes('"arguments"') || reason.includes('{"')) {
      continue;
    }
    // 중복 제거
    if (seen.has(reason)) {
      continue;
    }
    seen.add(reason);
    uniqueReasons.push(reason);

    // 최대 5개까지만
    if (uniqueReasons.length >= 5) {
      break;
    }
  }

  if (uniqueReasons.length === 0) {
    return null;
  }

  return (
    <List>
      {uniqueReasons.map((reason, index) => (
        <li key={index}>{reason}</li>
      ))}
    </List>
  );
};

export default ReasonList;
