import axios from 'axios';
import { ApiResponse } from '~/types/base';
import { API_HOST } from '~/constants';
import {
  CreateRoomRequest,
  CreateRoomResponse,
  RoomListResponse,
  FetchChattingRequest,
  ChattingResponseDto
} from '~/types/chatting';

// 채팅방 입장 시, 채팅방 정보를 얻음
export const createRoom = async (param: CreateRoomRequest) => {
  const room: ApiResponse<CreateRoomResponse> = await axios.post(
    `${API_HOST}/chat/room/create`,
    param
  );

  return room.data.data;
};

// 현재 채팅방 목록을 가져옴
export const fetchRoomList = async (userId: number) => {
  const roomList: ApiResponse<Array<RoomListResponse>> = await axios.get(
    `${API_HOST}/chat/roomList/${userId}`
  );

  return roomList.data.data;
};

// 채팅방의 채팅 데이터를 가져옴
export const fetchChatting = async (param: FetchChattingRequest) => {
  const { room_id, cursor } = param;
  const cursorParam = cursor !== null ? `&cursor=${cursor}` : '';
  const chatting: ApiResponse<Array<ChattingResponseDto>> = await axios.get(
    `${API_HOST}/chat/room?room_id=${room_id}${cursorParam}`
  );

  return chatting.data.data;
};

// 이미지 업로드 응답 타입
interface ImageUploadResponse {
  image_url: string;
  filename: string;
  originalname: string;
  size: number;
}

// 이미지 업로드
export const uploadImage = async (imageFile: File): Promise<string> => {
  const formData = new FormData();
  formData.append('image', imageFile);

  const response: ApiResponse<ImageUploadResponse> = await axios.post(
    `${API_HOST}/chat/upload/image`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  );

  return response.data.data.image_url;
};

// 메시지를 시크릿으로 변환
interface ConvertToSecretResponse {
  id: number;
  message: string;
  message_type: string;
  secret_id: string;
}

export const convertMessageToSecret = async (
  messageId: number,
  secretId: string
): Promise<ConvertToSecretResponse> => {
  const response: ApiResponse<ConvertToSecretResponse> = await axios.put(
    `${API_HOST}/chat/message/${messageId}/convert-to-secret`,
    { secret_id: secretId }
  );

  return response.data.data;
};
