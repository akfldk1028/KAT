import React, { Component } from 'react';
import styled from 'styled-components';
import { Dispatch, bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import { Header, Content, Footer } from '~/components/chattingRoom';
import SecurityAlert from '~/components/chattingRoom/SecurityAlert';
import SecretModePopup, { SecretOptions } from '~/components/chattingRoom/SecretModePopup';
import { SecurityAnalysis } from '~/types/security';
import { Portal } from '~/pages/Modal';
import { RootState } from '~/store/reducers';
import { ChatActions } from '~/store/actions/chat';
import { ProfileActions } from '~/store/actions/profile';
import { UserActions } from '~/store/actions/user';
import {
  ChangeChattingRoomDto,
  CreateRoomRequest,
  RoomType,
  ChattingRequestDto,
  FetchChattingRequest,
  ReadChatRequest,
  ReadChatResponse,
  UpdateRoomListDto
} from '~/types/chatting';
import { createRoom, uploadImage, convertMessageToSecret } from '~/apis/chat';
import { AddFriendRequestDto } from '~/types/friend';
import { UserResponseDto } from '~/types/user';
import { addFriendRequest } from '~/apis/friend';
import { analyzeImage, analyzeOutgoing } from '~/apis/agent';
import { createSecretMessage } from '~/apis/secret';
import {
  NotFriendWarning,
  DownBtn,
  MessageNotification
} from '~/components/chattingRoom/InfoBlock';

const Wrapper = styled.div`
  position: fixed;
  top: 0px;
  left: 0px;
  z-index: 99;
  width: 100%;
  height: 100vh;
  background: #b2c7d9;
`;

interface Props {
  rootState: RootState;
  chatActions: typeof ChatActions;
  profileActions: typeof ProfileActions;
  userActions: typeof UserActions;
}

interface State {
  isShowDownBtn: boolean;
  sendUserId: number | undefined;
  msg: string;
  selectedImage: File | null;
  imagePreview: string | null;
  securityAnalysis: SecurityAnalysis | null;
  isAnalyzing: boolean;
  pendingTextMessage: string | null;
  isTextAnalysis: boolean;
  showSecretPopup: boolean;
  lastSentMessageId: number | null;
}

let prevScrollHeight = 0;

class ChattingRoomContainer extends Component<Props, State> {
  messageRef: React.RefObject<HTMLDivElement>;

  state: State = {
    isShowDownBtn: false,
    sendUserId: undefined,
    msg: '',
    selectedImage: null,
    imagePreview: null,
    securityAnalysis: null,
    isAnalyzing: false,
    pendingTextMessage: null,
    isTextAnalysis: false,
    showSecretPopup: false,
    lastSentMessageId: null
  };

  constructor(props: Props) {
    super(props);
    this.messageRef = React.createRef<HTMLDivElement>();
    const userState = props.rootState.user;
    const chatState = props.rootState.chat;
    const roomList = userState.room_list;
    const findRoom = roomList.find(
      room => room.identifier === chatState.identifier
    );
    const participant = chatState.participant;

    const { changeChattingRoomInfo, fetchChatting } = props.chatActions;
    if (findRoom) {
      const { updateRoomList } = props.userActions;
      const updateRoomObj: UpdateRoomListDto = {
        room_id: findRoom.room_id,
        not_read_chat: 0
      };
      updateRoomList(updateRoomObj);
      const roomObj: ChangeChattingRoomDto = {
        ...findRoom,
        participant
      };
      changeChattingRoomInfo(roomObj);
      fetchChatting({
        room_id: findRoom.room_id,
        cursor: null
      });
    } else {
      const createRoomObj: CreateRoomRequest = {
        my_id: userState.id,
        type: chatState.type as RoomType,
        identifier: chatState.identifier,
        room_name: '',
        participant
      };
      createRoom(createRoomObj).then(room => {
        const roomObj: ChangeChattingRoomDto = {
          ...room,
          participant
        };
        changeChattingRoomInfo(roomObj);
      });
    }
  }

  componentDidMount() {
    this.messageRef.current!.addEventListener('scroll', this.handleScroll);
  }

  componentWillUnmount() {
    const socket = this.props.rootState.auth.socket;
    this.messageRef.current!.removeEventListener('scroll', this.handleScroll);
    socket!.off('readChat');
    this.updateRoom();
  }

  componentDidUpdate(prevProps: Props) {
    this.changeScroll(prevProps);
    this.updateFriendList(prevProps);
    this.readChat(prevProps);
  }

  handleScroll = () => {
    const messageRef = this.messageRef.current!;
    const scrollTop = messageRef.scrollTop;
    const chatState = this.props.rootState.chat;
    const chatting = chatState.chatting;
    const { fetchChatting } = this.props.chatActions;

    if (!chatState.isFetchChattingLoading && scrollTop === 0 && chatting.length > 0) {
      const requestObj: FetchChattingRequest = {
        room_id: chatState.room_id,
        cursor: chatting[0].id
      };
      fetchChatting(requestObj);
      prevScrollHeight = messageRef.scrollHeight;
    }

    if (prevScrollHeight - messageRef.scrollTop > messageRef.clientHeight + 1000) {
      this.setState({ ...this.state, isShowDownBtn: true });
    } else {
      this.setState({ ...this.state, isShowDownBtn: false, sendUserId: undefined, msg: '' });
    }
  };

  changeScroll = (prevProps: Props) => {
    const prevChatState = prevProps.rootState.chat;
    const chatState = this.props.rootState.chat;
    const userState = this.props.rootState.user;
    const messageRef = this.messageRef.current!;
    const prevChattingLen = prevChatState.chatting.length;
    const currChattingLen = chatState.chatting.length;
    const currScrollHeight = messageRef.scrollHeight;

    if (prevChattingLen !== currChattingLen) {
      if (prevChattingLen === 0) {
        this.pageDown();
      } else {
        const prevLastChat = prevChatState.chatting[prevChattingLen - 1];
        const currLastChat = chatState.chatting[currChattingLen - 1];
        if (prevChatState.chatting[0].id !== chatState.chatting[0].id) {
          messageRef.scrollTop = currScrollHeight - prevScrollHeight;
        } else if (prevLastChat.id !== currLastChat.id) {
          if (currLastChat.send_user_id === userState.id || prevScrollHeight - messageRef.scrollTop <= messageRef.clientHeight + 100) {
            this.pageDown();
          } else if (prevScrollHeight - messageRef.scrollTop > messageRef.clientHeight + 1000) {
            this.setState({
              ...this.state,
              isShowDownBtn: true,
              sendUserId: currLastChat.send_user_id,
              msg: currLastChat.message
            });
          }
        }
      }
      prevScrollHeight = currScrollHeight;
    }
  };

  updateFriendList = (prevProps: Props) => {
    const prevFriendList = prevProps.rootState.user.friends_list;
    const currentFriendList = this.props.rootState.user.friends_list;
    if (prevFriendList !== currentFriendList) {
      const chatState = this.props.rootState.chat;
      const { changeChattingRoomInfo } = this.props.chatActions;
      const participants = chatState.participant.map(participant => {
        const find = currentFriendList.find(friend => friend.id === participant.id);
        return find || participant;
      });
      changeChattingRoomInfo({ participant: participants });
    }
  };

  readChat = (prevProps: Props) => {
    const prevChatting = prevProps.rootState.chat.chatting;
    const chatState = this.props.rootState.chat;
    const currChatting = chatState.chatting;
    const prevChattingLen = prevChatting.length;
    const currChattingLen = currChatting.length;

    if (prevChattingLen !== currChattingLen) {
      const lastReadChatId = chatState.last_read_chat_id;
      const lastChat = currChatting[currChattingLen - 1];
      if (lastChat.id !== lastReadChatId) {
        const socket = this.props.rootState.auth.socket;
        const userState = this.props.rootState.user;
        const { readChatting, changeChattingRoomInfo } = this.props.chatActions;
        const currRange = [lastReadChatId, lastChat.id];

        if (lastChat.send_user_id !== userState.id) {
          const roomObj: ChangeChattingRoomDto = { last_read_chat_id: lastChat.id };
          changeChattingRoomInfo(roomObj);
          readChatting(currRange);
          const obj: ReadChatRequest = {
            user_id: userState.id,
            room_id: chatState.room_id,
            type: chatState.type as RoomType,
            participant: chatState.participant,
            last_read_chat_id_range: currRange
          };
          socket!.emit('readChat', obj);
        } else {
          const roomObj: ChangeChattingRoomDto = { last_read_chat_id: lastChat.id };
          changeChattingRoomInfo(roomObj);
        }

        socket!.off('readChat');
        socket!.on('readChat', (res: ReadChatResponse) => {
          if (chatState.room_id === res.room_id) {
            const range = res.last_read_chat_id_range;
            readChatting(range);
          }
        });
      }
    }
  };

  updateRoom = () => {
    const { updateRoomList } = this.props.userActions;
    const chatState = this.props.rootState.chat;
    const chatting = chatState.chatting;
    const chattingLen = chatting.length;
    if (chattingLen > 0) {
      updateRoomList({
        room_id: chatState.room_id,
        last_read_chat_id: chatting[chattingLen - 1].id
      });
    }
  };

  pageDown = () => {
    const messageRef = this.messageRef.current!;
    messageRef.scrollTop = messageRef.scrollHeight;
  };

  handleImageSelect = async (file: File) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      this.setState({
        selectedImage: file,
        imagePreview: reader.result as string,
        isAnalyzing: true,
        securityAnalysis: null
      });
    };
    reader.readAsDataURL(file);

    try {
      const analysis = await analyzeImage(file);
      this.setState({ securityAnalysis: analysis, isAnalyzing: false });
    } catch (error) {
      console.error('Image analysis failed:', error);
      this.setState({
        securityAnalysis: {
          risk_level: 'LOW',
          reasons: ['Analysis server connection failed'],
          recommended_action: 'Check server connection',
          is_secret_recommended: false
        },
        isAnalyzing: false
      });
    }
  };

  handleSecurityConfirm = async () => {
    const { selectedImage } = this.state;
    if (!selectedImage) {
      this.clearImageState();
      return;
    }

    try {
      const imageUrl = await uploadImage(selectedImage);
      const userState = this.props.rootState.user;
      const chatState = this.props.rootState.chat;
      const authState = this.props.rootState.auth;
      const isGroup = chatState.type === 'group';
      const isMe = chatState.participant[0].id === userState.id;

      const chattingRequest: ChattingRequestDto = {
        room_id: chatState.room_id,
        type: chatState.type as RoomType,
        participant: chatState.participant,
        send_user_id: userState.id,
        message: '[Image]',
        not_read: !isGroup && isMe ? 0 : chatState.participant.length,
        message_type: 'image',
        image_url: imageUrl
      };

      authState.socket?.emit('message', chattingRequest);
      this.clearImageState();
    } catch (error) {
      console.error('Image upload failed:', error);
      alert('Failed to send image.');
      this.clearImageState();
    }
  };

  handleSecurityCancel = () => {
    this.clearAnalysisState();
  };

  clearImageState = () => {
    this.clearAnalysisState();
  };

  clearAnalysisState = () => {
    this.setState({
      selectedImage: null,
      imagePreview: null,
      securityAnalysis: null,
      isAnalyzing: false,
      pendingTextMessage: null,
      isTextAnalysis: false
    });
  };

  handleTextConfirm = () => {
    this.clearAnalysisState();
  };

  handleSecretSend = () => {
    this.setState({ showSecretPopup: true });
  };

  handleNormalSend = () => {
    this.clearAnalysisState();
  };

  handleSecretConfirm = async (options: SecretOptions) => {
    const chatState = this.props.rootState.chat;
    const userState = this.props.rootState.user;
    const pendingMessage = this.state.pendingTextMessage;
    const selectedImage = this.state.selectedImage;
    const { updateChatMessage } = this.props.chatActions;

    if (selectedImage) {
      try {
        const imageUrl = await uploadImage(selectedImage);
        const response = await createSecretMessage({
          room_id: chatState.room_id,
          sender_id: userState.id,
          message: imageUrl,
          message_type: 'image',
          expiry_seconds: options.expirySeconds,
          require_auth: options.requireAuth,
          prevent_capture: options.preventCapture
        });
        // 순서: 에이전트 알림 먼저, 시크릿 링크 나중에
        this.showSecretSuccessAlert();
        this.sendSecretMessage(response.secret_id);
        console.log('Secret image sent:', response.secret_id);
      } catch (error) {
        console.error('Secret image send failed:', error);
        alert('Failed to send secret image.');
      }
      this.setState({ showSecretPopup: false });
      this.clearAnalysisState();
      return;
    }

    if (!pendingMessage) {
      console.error('No message to send');
      this.setState({ showSecretPopup: false });
      this.clearAnalysisState();
      return;
    }

    try {
      const response = await createSecretMessage({
        room_id: chatState.room_id,
        sender_id: userState.id,
        message: pendingMessage,
        message_type: 'text',
        expiry_seconds: options.expirySeconds,
        require_auth: options.requireAuth,
        prevent_capture: options.preventCapture
      });

      console.log('Secret message created:', response);

      const lastMessage = chatState.chatting[chatState.chatting.length - 1];
      if (lastMessage && lastMessage.message === pendingMessage && lastMessage.send_user_id === userState.id) {
        await convertMessageToSecret(lastMessage.id, response.secret_id);
        updateChatMessage({
          id: lastMessage.id,
          message: '[SecretLink]',
          message_type: 'secret',
          secret_id: response.secret_id
        });
        console.log('Message converted to secret:', lastMessage.id);
        // 기존 메시지 변환의 경우 에이전트 알림만
        this.showSecretSuccessAlert();
      } else {
        console.warn('Could not find message to convert, sending new secret message');
        // 순서: 에이전트 알림 먼저, 시크릿 링크 나중에
        this.showSecretSuccessAlert();
        this.sendSecretMessage(response.secret_id);
      }
    } catch (error) {
      console.error('Secret message creation failed:', error);
      alert('Failed to create secret message.');
    }

    this.setState({ showSecretPopup: false });
    this.clearAnalysisState();
  };

  handleSecretCancel = () => {
    this.setState({ showSecretPopup: false });
  };

  showSecretSuccessAlert = () => {
    // 에이전트 알림을 채팅 메시지로 전송 (채팅방에 영구 저장)
    this.sendAgentAlertMessage('"민감정보를 시크릿 전송으로 보냈어요."');
  };

  sendAgentAlertMessage = (msg: string) => {
    const userState = this.props.rootState.user;
    const chatState = this.props.rootState.chat;
    const authState = this.props.rootState.auth;

    const chattingRequest: ChattingRequestDto = {
      room_id: chatState.room_id,
      type: chatState.type as RoomType,
      participant: chatState.participant,
      send_user_id: userState.id,
      message: msg,
      not_read: 0,
      message_type: 'agent_alert'
    };

    authState.socket?.emit('message', chattingRequest);
  };

  sendTextMessage = (msg: string) => {
    const userState = this.props.rootState.user;
    const chatState = this.props.rootState.chat;
    const authState = this.props.rootState.auth;
    const isMe = chatState.participant[0].id === userState.id;
    const isGroup = chatState.type === 'group';

    const chattingRequest: ChattingRequestDto = {
      room_id: chatState.room_id,
      type: chatState.type as RoomType,
      participant: chatState.participant,
      send_user_id: userState.id,
      message: msg,
      not_read: !isGroup && isMe ? 0 : chatState.participant.length
    };

    authState.socket?.emit('message', chattingRequest);
  };

  sendSecretMessage = (secretId: string) => {
    const userState = this.props.rootState.user;
    const chatState = this.props.rootState.chat;
    const authState = this.props.rootState.auth;
    const isMe = chatState.participant[0].id === userState.id;
    const isGroup = chatState.type === 'group';

    const chattingRequest: ChattingRequestDto = {
      room_id: chatState.room_id,
      type: chatState.type as RoomType,
      participant: chatState.participant,
      send_user_id: userState.id,
      message: '[SecretLink]',
      not_read: !isGroup && isMe ? 0 : chatState.participant.length,
      message_type: 'secret',
      secret_id: secretId
    };

    authState.socket?.emit('message', chattingRequest);
  };

  render() {
    const userState = this.props.rootState.user;
    const chatState = this.props.rootState.chat;
    const roomName = chatState.room_name || chatState.participant[0].name;
    const isMe = chatState.participant[0].id === userState.id;
    const isGroup = chatState.type === 'group';
    const { hideChattingRoom } = this.props.chatActions;
    const { showProfile } = this.props.profileActions;

    const onChatSumbmit = async (msg: string) => {
      // 1. Send message first (optimistic UI)
      this.sendTextMessage(msg);

      // 2. Show loading (AI analyzing)
      this.setState({
        isAnalyzing: true,
        pendingTextMessage: msg,
        isTextAnalysis: true
      });

      // 3. Start AI analysis in background
      try {
        const analysis = await analyzeOutgoing(msg, true);

        // 4. If sensitive info detected, show popup
        if (analysis.risk_level !== 'LOW' && analysis.is_secret_recommended) {
          this.setState({
            securityAnalysis: analysis,
            isAnalyzing: false
          });
        } else {
          // Safe - hide loading
          this.clearAnalysisState();
        }
      } catch (error) {
        console.error('Text analysis failed:', error);
        // On failure, hide loading (already sent)
        this.clearAnalysisState();
      }
    };

    const isFriend: boolean =
      isGroup ||
      isMe ||
      !!userState.friends_list.find(friend => friend.id === chatState.participant[0].id);

    const onAddFriendClick = async (friend: UserResponseDto) => {
      const my_id = userState.id;
      const friend_id = friend.id;
      const friend_name = friend.name;
      const { addFriend } = this.props.userActions;
      const request: AddFriendRequestDto = { my_id, friend_id, friend_name };
      try {
        await addFriendRequest(request);
        await addFriend(friend);
      } catch (err) {
        alert('Failed to add friend');
      }
    };

    const contentProps = {
      myId: userState.id,
      participant: chatState.participant,
      chattingList: chatState.chatting,
      messageRef: this.messageRef,
      showProfile
    };

    const renderNotification = () => {
      if (!!this.state.sendUserId) {
        const findSendUser = chatState.participant.find(person => person.id === this.state.sendUserId);
        return (
          <MessageNotification
            user={findSendUser}
            msg={this.state.msg}
            onDownClick={this.pageDown}
          />
        );
      }
      return this.state.isShowDownBtn ? <DownBtn onDownClick={this.pageDown} /> : null;
    };

    const renderSecurityAlert = () => {
      if (this.state.showSecretPopup) {
        return null;
      }

      if (this.state.isAnalyzing) {
        return (
          <SecurityAlert
            analysis={{
              risk_level: 'LOW',
              reasons: [],
              recommended_action: '',
              is_secret_recommended: false
            }}
            isLoading={true}
            onSecretSend={() => {}}
            onNormalSend={() => {}}
            onCancel={this.handleSecurityCancel}
          />
        );
      }

      if (this.state.securityAnalysis) {
        return (
          <SecurityAlert
            analysis={this.state.securityAnalysis}
            imagePreview={this.state.imagePreview || undefined}
            onSecretSend={this.handleSecretSend}
            onNormalSend={this.handleNormalSend}
            onCancel={this.handleSecurityCancel}
          />
        );
      }

      return null;
    };

    const renderSecretPopup = () => {
      if (!this.state.showSecretPopup) {
        return null;
      }

      return (
        <SecretModePopup
          onConfirm={this.handleSecretConfirm}
          onCancel={this.handleSecretCancel}
        />
      );
    };

    return (
      <Portal>
        <Wrapper>
          <Header room_name={roomName} hideRoom={hideChattingRoom} />
          <Content {...contentProps}>
            {isFriend ? null : (
              <NotFriendWarning
                onAddFriendClick={() => onAddFriendClick(chatState.participant[0])}
              />
            )}
            {renderNotification()}
          </Content>
          <Footer
            onChatSumbmit={onChatSumbmit}
            onImageSelect={this.handleImageSelect}
          />
          {renderSecurityAlert()}
          {renderSecretPopup()}
        </Wrapper>
      </Portal>
    );
  }
}

const mapStateToProps = (state: RootState) => ({
  rootState: state
});

const mapDispatchToProps = (dispatch: Dispatch) => ({
  chatActions: bindActionCreators(ChatActions, dispatch),
  profileActions: bindActionCreators(ProfileActions, dispatch),
  userActions: bindActionCreators(UserActions, dispatch)
});

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(ChattingRoomContainer);
