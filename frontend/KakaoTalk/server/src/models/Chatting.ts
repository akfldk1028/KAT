import { Model } from 'sequelize';

export type MessageType = 'text' | 'image' | 'secret';

export default class Chatting extends Model {
  public id!: number;
  public room_id!: number;
  public send_user_id!: number;
  public message!: string;
  public not_read!: number;
  public message_type!: MessageType;
  public image_url!: string | null;

  public readonly createdAt!: Date;
  public readonly updatedAt!: Date;
}
