import logging
import datetime

from data import modules, cache_memory
from db.tables import get_session, WaUser, Topic, Message, MessageToSend, Settings


_logger = logging.getLogger(__name__)
cache = cache_memory.my_cache


def create_user_and_topic(wa_id: str, name: str, topic_id: int):
    """
    Create user and topic
    :param wa_id: the number of the user
    :param name: the name of the user and the topic
    :param topic_id: the id of the topic
    :return:
    """

    _logger.debug(f"create user wa_id:{wa_id}, name:{name}, topic_id:{topic_id}")
    cache.delete(
        cache_name="get_user_by_wa_id", cache_id=cache.build_cache_id(wa_id=wa_id)
    )
    cache.delete(
        cache_name="get_topic_by_topic_id",
        cache_id=cache.build_cache_id(topic_id=topic_id),
    )

    with get_session() as session:
        topic = Topic(
            topic_id=topic_id,
            name=name,
            created_at=datetime.datetime.now(),
        )
        user = WaUser(
            wa_id=wa_id,
            name=name,
            topic=topic,
            created_at=datetime.datetime.now(),
        )

        session.add_all((user, topic))
        session.commit()


@cache.cachable(cache_name="get_user_by_wa_id", params=("wa_id",))
def get_user_by_wa_id(*, wa_id: str) -> WaUser:
    """
    Get user by wa_id
    :param wa_id: the number of the user
    :return: the user
    """

    with get_session() as session:
        return session.query(WaUser).filter(WaUser.wa_id == wa_id).one()


@cache.cachable(cache_name="get_topic_by_topic_id", params=("topic_id",))
def get_topic_by_topic_id(*, topic_id: int) -> Topic:
    """
    Get topic by topic_id
    :param topic_id: the id of the topic
    :return: the topic
    """
    with get_session() as session:
        return session.query(Topic).filter(Topic.topic_id == topic_id).one()


def update_user(*, wa_id: str, **kwargs):
    """
    Update user
    :param wa_id: the number of the user
    :param kwargs: the fields to update
    :return:
    """

    _logger.debug(f"update user wa_id:{wa_id}, kwargs:{kwargs}")
    user = get_user_by_wa_id(wa_id=wa_id)
    cache.delete(
        cache_name="get_topic_by_topic_id",
        cache_id=cache.build_cache_id(topic_id=user.topic.topic_id),
    )
    cache.delete(
        cache_name="get_user_by_wa_id", cache_id=cache.build_cache_id(wa_id=wa_id)
    )

    with get_session() as session:
        session.query(WaUser).filter(WaUser.wa_id == wa_id).update(kwargs)
        session.commit()


def update_topic(*, topic_id: int, **kwargs):
    """
    Update topic
    :param topic_id: the id of the topic
    :param kwargs: the fields to update
    :return:
    """

    _logger.debug(f"update topic topic_id:{topic_id}, kwargs:{kwargs}")
    cache.delete(
        cache_name="get_topic_by_topic_id",
        cache_id=cache.build_cache_id(topic_id=topic_id),
    )
    topic = get_topic_by_topic_id(topic_id=topic_id)
    cache.delete(
        cache_name="get_user_by_wa_id",
        cache_id=cache.build_cache_id(wa_id=topic.user.wa_id),
    )

    with get_session() as session:
        session.query(Topic).filter(Topic.topic_id == topic_id).update(kwargs)
        session.commit()


# message


def create_message(*, wa_id: str, topic_id: int, wa_msg_id: str, topic_msg_id: int):
    """
    Create message
    :param wa_id: the number of the user
    :param topic_id: the id of the topic
    :param wa_msg_id: the id of the message in whatsapp
    :param topic_msg_id: the id of the message in topic
    :return:
    """
    _logger.debug(
        f"create message wa_id:{wa_id}, topic_id:{topic_id}, wa_msg_id:{wa_msg_id}, topic_msg_id:{topic_msg_id}"
    )
    with get_session() as session:
        user = session.query(WaUser).filter(WaUser.wa_id == wa_id).one()
        topic = session.query(Topic).filter(Topic.topic_id == topic_id).one()
        message = Message(
            wa_msg_id=wa_msg_id,
            topic_msg_id=topic_msg_id,
            topic=topic,
            user=user,
            created_at=datetime.datetime.now(),
        )

        session.add(message)
        session.commit()


@cache.cachable(cache_name="get_message", params=("topic_msg_id", "wa_msg_id"))
def get_message(*, topic_msg_id: int | None, wa_msg_id: str | None) -> Message:
    """
    Get message by topic_msg_id or wa_msg_id
    :param topic_msg_id: the id of the message in topic
    :param wa_msg_id: the id of the message in whatsapp
    :return: the message
    """
    with get_session() as session:
        if topic_msg_id:
            return (
                session.query(Message)
                .filter(Message.topic_msg_id == topic_msg_id)
                .one()
            )
        return session.query(Message).filter(Message.wa_msg_id == wa_msg_id).one()


# message to send


def create_message_to_send(*, type_event: modules.EventType, text: str):
    """
    Create message to send
    :param type_event: the type of the event
    :param text: the text of the message
    :return:
    """

    _logger.debug(f"create message to send, type_event:{type_event}, text:{text}")
    cache.delete(
        cache_name="get_message_to_send",
        cache_id=cache.build_cache_id(type_event=type_event),
    )

    with get_session() as session:
        message_to_send = MessageToSend(
            type_event=type_event,
            text=text,
            created_at=datetime.datetime.now(),
        )

        session.add(message_to_send)
        session.commit()


@cache.cachable(cache_name="get_message_to_send", params=("type_event",))
def get_message_to_send(*, type_event: str) -> MessageToSend:
    """
    Get message to send by type_event
    :param type_event: the type of the event
    :return: the message to send
    """
    with get_session() as session:
        return (
            session.query(MessageToSend)
            .filter(MessageToSend.type_event == type_event)
            .one()
        )


def update_message_to_send(*, type_event: str, **kwargs):
    """
    Update message to send
    :param type_event: the type of the event
    :param kwargs: the fields to update
    :return:
    """

    _logger.debug(f"update message to send, type_event:{type_event}, kwargs:{kwargs}")
    cache.delete(
        cache_name="get_message_to_send",
        cache_id=cache.build_cache_id(type_event=type_event),
    )

    with get_session() as session:
        session.query(MessageToSend).filter(
            MessageToSend.type_event == type_event
        ).update(kwargs)
        session.commit()


# settings


def create_settings(*, chat_opened_enable: bool = False, welcome_msg: bool = False):
    """
    Create settings
    :param chat_opened_enable: the status of the chat
    :param welcome_msg: the status of the welcome message
    :return:
    """

    _logger.debug(
        f"create settings, chat_opened_enable:{chat_opened_enable}, welcome_msg:{welcome_msg}"
    )
    cache.delete(cache_name="get_settings")

    with get_session() as session:
        settings = Settings(
            chat_opened_enable=chat_opened_enable,
            welcome_msg=welcome_msg,
        )

        session.add(settings)
        session.commit()


@cache.cachable(cache_name="get_settings")
def get_settings() -> Settings:
    """
    Get settings
    :return: the settings
    """
    with get_session() as session:
        return session.query(Settings).one()


def update_settings(**kwargs):
    """
    Update settings
    :param kwargs: the fields to update
    :return:
    """

    _logger.debug(f"update settings, kwargs:{kwargs}")
    cache.delete(cache_name="get_settings")
    with get_session() as session:
        session.query(Settings).update(kwargs)
        session.commit()
