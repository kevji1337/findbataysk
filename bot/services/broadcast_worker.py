"""Background worker for persisted broadcast jobs."""

import asyncio
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter
from loguru import logger

from bot.database.repository import BroadcastJobRepository, UserRepository


class BroadcastWorker:
    """Runs broadcast jobs in background with throttle and retry."""

    def __init__(self, bot: Bot, poll_interval_seconds: float = 1.0):
        self.bot = bot
        self.poll_interval_seconds = poll_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run_loop(), name="broadcast-worker")
        logger.info("broadcast_worker_started")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("broadcast_worker_stopped")

    async def _run_loop(self) -> None:
        while not self._stopped.is_set():
            try:
                job = await BroadcastJobRepository.acquire_next_pending()
                if not job:
                    await asyncio.sleep(self.poll_interval_seconds)
                    continue
                await self._process_job(job.id)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("broadcast_worker_loop_error: {}", e)
                await asyncio.sleep(self.poll_interval_seconds)

    async def _process_job(self, job_id: int) -> None:
        job = await BroadcastJobRepository.get_by_id(job_id)
        if not job:
            return

        try:
            all_user_ids = await UserRepository.get_broadcast_telegram_ids()
            start_offset = max(0, job.processed_users)
            remaining_user_ids = all_user_ids[start_offset:]

            for user_id in remaining_user_ids:
                sent_delta = 0
                blocked_delta = 0
                failed_delta = 0

                try:
                    await self._send_with_retry(
                        target_chat_id=user_id,
                        source_chat_id=job.source_chat_id,
                        source_message_id=job.source_message_id,
                    )
                    sent_delta = 1
                except TelegramForbiddenError:
                    blocked_delta = 1
                    await UserRepository.mark_bot_blocked(user_id)
                except Exception:
                    failed_delta = 1

                await BroadcastJobRepository.increment_progress(
                    job_id=job.id,
                    sent_delta=sent_delta,
                    blocked_delta=blocked_delta,
                    failed_delta=failed_delta,
                )

                await asyncio.sleep(max(0.0, float(job.throttle_seconds)))

            await BroadcastJobRepository.mark_done(job.id)
            await self._notify_admin_done(job.id)
        except Exception as e:
            await BroadcastJobRepository.mark_retry_or_failed(job.id, str(e))
            logger.exception("broadcast_job_failed job_id={}: {}", job.id, e)

    async def _send_with_retry(
        self,
        *,
        target_chat_id: int,
        source_chat_id: int,
        source_message_id: int,
        max_attempts: int = 3,
    ) -> None:
        for attempt in range(1, max_attempts + 1):
            try:
                await self.bot.copy_message(
                    chat_id=target_chat_id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                )
                return
            except TelegramRetryAfter as e:
                await asyncio.sleep(float(e.retry_after))
            except TelegramNetworkError:
                await asyncio.sleep(0.5 * attempt)
            except TelegramForbiddenError:
                raise
            except Exception:
                if attempt >= max_attempts:
                    raise
                await asyncio.sleep(0.5 * attempt)

    async def _notify_admin_done(self, job_id: int) -> None:
        job = await BroadcastJobRepository.get_by_id(job_id)
        if not job:
            return

        text = (
            "📬 <b>Рассылка завершена</b>\n\n"
            f"Job ID: <b>{job.id}</b>\n"
            f"Всего пользователей: <b>{job.total_users}</b>\n"
            f"Обработано: <b>{job.processed_users}</b>\n"
            f"Успешно: <b>{job.sent_count}</b>\n"
            f"Заблокировали бота: <b>{job.blocked_count}</b>\n"
            f"Ошибок: <b>{job.failed_count}</b>"
        )
        try:
            await self.bot.send_message(chat_id=job.created_by_admin_id, text=text)
        except Exception as e:
            logger.warning("broadcast_done_notify_failed job_id={} error={}", job.id, e)
