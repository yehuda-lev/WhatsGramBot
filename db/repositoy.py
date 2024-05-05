import logging
import datetime

from sqlalchemy import exists, func

from db.tables import get_session, WaUser, Topic, Message


_logger = logging.getLogger(__name__)


def create_user_and_topic(wa_id: str, name: str, topic_id: int):
    """
    Create user and topic
    :param wa_id: the number of the user
    :param name: the name of the user and the topic
    :param topic_id: the id of the topic
    :return:
    """
    _logger.debug(f"create user wa_id:{wa_id}, name:{name}, topic_id:{topic_id}")
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


def get_user_by_wa_id(*, wa_id: str) -> WaUser:
    """
    Get user by wa_id
    :param wa_id: the number of the user
    :return: the user
    """
    with get_session() as session:
        return session.query(WaUser).filter(WaUser.wa_id == wa_id).one()


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
    with get_session() as session:
        session.query(Topic).filter(Topic.topic_id == topic_id).update(kwargs)
        session.commit()


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
