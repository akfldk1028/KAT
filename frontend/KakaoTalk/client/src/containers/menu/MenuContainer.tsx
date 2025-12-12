import React, { Component } from 'react';
import styled from 'styled-components';
import { Redirect } from 'react-router-dom';
import { connect } from 'react-redux';
import { Dispatch, bindActionCreators } from 'redux';
import { Socket } from 'socket.io-client';
import { MenuRoute } from '~/routes';
import { MenuSideBar } from '~/components/menu';
import { AuthActions } from '~/store/actions/auth';
import { UserActions } from '~/store/actions/user';
import { ChatActions } from '~/store/actions/chat';
import { RootState } from '~/store/reducers';
import { PAGE_PATHS } from '~/constants';
import { Auth } from '~/types/auth';
import { ProfileContainer, ChattingRoomContainer } from '~/containers';
import { ChattingResponseDto, UpdateRoomListDto } from '~/types/chatting';
// Note: analyzeIncoming은 Node.js 서버(sockets/index.ts)에서 호출하고
// security_analysis를 WebSocket 응답에 포함해서 보냄 - 클라이언트에서 중복 호출 불필요

const Wrapper = styled.main`
  width: 100%;
  display: flex;
`;

interface Props {
  rootState: RootState;
  authActions: typeof AuthActions;
  userActions: typeof UserActions;
  chatActions: typeof ChatActions;
}

class MenuContainer extends Component<Props> {
  constructor(props: Props) {
    super(props);
    const auth: Auth | undefined = props.rootState.auth.auth;
    if (auth) {
      const socket = props.rootState.auth.socket as typeof Socket;
      const { updateChatSecurityHint } = props.chatActions;

      props.userActions.fetchUser(auth.user_id);
      props.userActions.fetchFriends(auth.id);
      props.userActions.fetchRoomList(auth.id);
      socket.emit('join', auth.id.toString());

      // 메시지 수신 이벤트
      socket.on('message', async (response: ChattingResponseDto) => {
        this.updateRooms(response);
      });

      // Agent B 보안 힌트 이벤트 (비동기, 나중에 표시)
      socket.on('security_hint', (hint: { message_id: number; room_id: number; security_analysis: any }) => {
        console.log('[Agent B] 보안 힌트 수신:', {
          message_id: hint.message_id,
          risk_level: hint.security_analysis.risk_level
        });
        updateChatSecurityHint(hint.message_id, hint.security_analysis);
      });
    }
  }

  updateRooms = async (response: ChattingResponseDto) => {
    const userState = this.props.rootState.user;
    const chatState = this.props.rootState.chat;
    const roomList = userState.room_list;
    const { fetchRoomList, updateRoomList } = this.props.userActions;

    const findRoom = roomList.find(room => room.room_id === response.room_id);
    if (findRoom) {
      const haveReadChat = response.room_id === chatState.room_id;
      const notReadChat = haveReadChat ? 0 : findRoom.not_read_chat + 1;
      const lastReadChatId = haveReadChat
        ? response.id
        : findRoom.last_read_chat_id;
      const updateRoomObj: UpdateRoomListDto = {
        room_id: response.room_id,
        last_chat: response.message,
        updatedAt: response.createdAt,
        not_read_chat: notReadChat,
        last_read_chat_id: lastReadChatId
      };
      updateRoomList(updateRoomObj);
    } else {
      await fetchRoomList(userState.id);
    }
  };

  async componentDidUpdate(prevProps: Props) {
    const chatState = this.props.rootState.chat;
    if (prevProps.rootState.chat.room_id !== chatState.room_id) {
      const socket = this.props.rootState.auth.socket as typeof Socket;
      const { addChatting, updateChatSecurityHint } = this.props.chatActions;

      // 기존 이벤트 리스너 제거
      await socket.off('message');
      await socket.off('security_hint');

      // 메시지 수신 이벤트 (즉시 표시)
      await socket.on('message', async (response: ChattingResponseDto) => {
        if (response.room_id === chatState.room_id) {
          await addChatting(response);
        }
        await this.updateRooms(response);
      });

      // Agent B 보안 힌트 이벤트 (비동기, 나중에 표시)
      await socket.on('security_hint', (hint: { message_id: number; room_id: number; security_analysis: any }) => {
        console.log('[Agent B] 보안 힌트 수신:', {
          message_id: hint.message_id,
          risk_level: hint.security_analysis.risk_level,
          reasons: hint.security_analysis.reasons
        });

        // 해당 메시지에 보안 힌트 추가
        if (hint.room_id === chatState.room_id) {
          updateChatSecurityHint(hint.message_id, hint.security_analysis);
        }
      });
    }
  }

  render() {
    const { logout } = this.props.authActions;
    const authState = this.props.rootState.auth;
    const token = authState.auth;
    const socket = authState.socket as typeof Socket;
    const chatState = this.props.rootState.chat;
    const userState = this.props.rootState.user;
    const roomList = userState.room_list;

    // 로그인 상태가 아니라면 로그인 메뉴로 이동합니다.
    if (!token) {
      return <Redirect to={PAGE_PATHS.LOGIN} />;
    }

    return (
      <React.Fragment>
        <ProfileContainer />
        {chatState.isChattingRoomShown ? <ChattingRoomContainer /> : null}
        <Wrapper>
          <MenuSideBar roomList={roomList} socket={socket} logout={logout} />
          <MenuRoute />
        </Wrapper>
      </React.Fragment>
    );
  }
}

const mapStateToProps = (state: RootState) => ({
  rootState: state
});
const mapDispatchToProps = (dispatch: Dispatch) => ({
  authActions: bindActionCreators(AuthActions, dispatch),
  userActions: bindActionCreators(UserActions, dispatch),
  chatActions: bindActionCreators(ChatActions, dispatch)
});

export default connect(mapStateToProps, mapDispatchToProps)(MenuContainer);
