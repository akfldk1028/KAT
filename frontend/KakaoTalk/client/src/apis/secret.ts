/**
 * Secret Message API
 * 시크릿 메시지 생성, 조회, 상태 확인
 */
import axios from 'axios';
import { SECRET_HOST } from '~/constants';

export interface SecretMessageCreate {
  room_id: number;
  sender_id: number;
  message: string;
  message_type?: 'text' | 'image';
  image_url?: string;
  expiry_seconds: number;
  require_auth: boolean;
  prevent_capture: boolean;
}

export interface SecretMessageResponse {
  secret_id: string;
  room_id: number;
  sender_id: number;
  message_type: string;
  expiry_seconds: number;
  require_auth: boolean;
  prevent_capture: boolean;
  created_at: string;
  expires_at: string;
}

export interface SecretMessageContent {
  secret_id: string;
  message: string;
  message_type: string;
  image_url?: string;
  is_expired: boolean;
  prevent_capture: boolean;
  remaining_seconds: number;
}

export interface SecretMessageStatus {
  secret_id: string;
  is_viewed: boolean;
  viewed_at?: string;
  is_expired: boolean;
  remaining_seconds: number;
  created_at: string;
  expires_at: string;
  // 발신자가 자신의 메시지 확인용
  message?: string;
  message_type?: string;
  image_url?: string;
}

export interface ExtendSecretResponse {
  status: string;
  secret_id: string;
  added_seconds: number;
  new_expires_at: string;
  remaining_seconds: number;
}

/**
 * 시크릿 메시지 생성
 */
export const createSecretMessage = async (
  data: SecretMessageCreate
): Promise<SecretMessageResponse> => {
  const response = await axios.post<SecretMessageResponse>(
    `${SECRET_HOST}/create`,
    data,
    { timeout: 10000 }
  );
  return response.data;
};

/**
 * 시크릿 메시지 열람
 */
export const viewSecretMessage = async (
  secretId: string
): Promise<SecretMessageContent> => {
  const response = await axios.get<SecretMessageContent>(
    `${SECRET_HOST}/view/${secretId}`,
    { timeout: 10000 }
  );
  return response.data;
};

/**
 * 시크릿 메시지 상태 확인 (발신자용)
 */
export const checkSecretStatus = async (
  secretId: string
): Promise<SecretMessageStatus> => {
  const response = await axios.get<SecretMessageStatus>(
    `${SECRET_HOST}/status/${secretId}`,
    { timeout: 5000 }
  );
  return response.data;
};

/**
 * 시크릿 메시지 수동 만료
 */
export const expireSecretMessage = async (
  secretId: string
): Promise<{ status: string; secret_id: string }> => {
  const response = await axios.delete(
    `${SECRET_HOST}/expire/${secretId}`,
    { timeout: 5000 }
  );
  return response.data;
};

/**
 * 시크릿 메시지 시간 연장
 */
export const extendSecretMessage = async (
  secretId: string,
  additionalSeconds: number
): Promise<ExtendSecretResponse> => {
  const response = await axios.put<ExtendSecretResponse>(
    `${SECRET_HOST}/extend/${secretId}`,
    { additional_seconds: additionalSeconds },
    { timeout: 5000 }
  );
  return response.data;
};
