"""
Message simulator for generating realistic conversation history.
Simulates customer support conversations for Kommo CRM timeline.
"""

import logging
import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class ContactTag(Enum):
    """Contact categorization tags"""
    SUPPORT = "Support"
    DOCS = "Docs"
    REFUND = "Refund"
    BILLING = "Billing"


@dataclass
class MessageSimulation:
    """Simulated message for timeline"""
    text: str
    timestamp: datetime
    is_incoming: bool  # True = from customer, False = from support
    message_type: str  # "question", "response", "order", "complaint"
    tags: List[ContactTag]


class MessageSimulator:
    """
    Generates realistic customer conversation simulations.
    
    Attributes:
        logger: Logger instance
        templates: Message template library
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize message simulator.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.templates = self._load_templates()
        
        self.logger.info("Initialized MessageSimulator")
    
    def _load_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Load message templates by category.
        
        Returns:
            Dictionary of templates organized by conversation type
        """
        templates = {
            "support": {
                "customer_questions": [
                    "Здравствуйте! Подскажите, как активировать мой заказ?",
                    "Привет, есть вопрос по работе с вашим продуктом",
                    "Не могу разобраться с настройками, помогите пожалуйста",
                    "Добрый день! Возникла проблема с доступом",
                    "Здравствуйте! Можете помочь с настройкой?",
                    "Привет! У меня не получается запустить",
                    "Добрый день, нужна помощь техподдержки"
                ],
                "support_responses": [
                    "Здравствуйте! Конечно помогу. Опишите подробнее проблему",
                    "Привет! Давайте разберемся. Что именно не работает?",
                    "Добрый день! С радостью помогу. Какие именно настройки?",
                    "Здравствуйте! Проверьте пожалуйста почту, выслал инструкцию",
                    "Привет! Уже проверяю. Сейчас все настроим",
                    "Добрый день! Понял вашу проблему. Сейчас решим",
                    "Здравствуйте! Спасибо за обращение. Помогу разобраться"
                ],
                "resolutions": [
                    "Отлично, все заработало! Спасибо большое!",
                    "Супер, теперь все понятно. Благодарю за помощь!",
                    "Ура, проблема решена! Очень благодарен",
                    "Все получилось, спасибо за оперативную помощь!",
                    "Класс! Теперь работает. Большое спасибо!"
                ]
            },
            "sales": {
                "customer_questions": [
                    "Здравствуйте! Хочу купить ваш продукт, расскажите подробнее",
                    "Привет! Какие у вас есть тарифы?",
                    "Добрый день! Есть ли скидки для новых клиентов?",
                    "Здравствуйте! Подойдет ли мне базовый тариф?",
                    "Привет! Можно узнать о способах оплаты?",
                    "Добрый день! Интересует ваш сервис",
                    "Здравствуйте! Какая стоимость подписки?"
                ],
                "support_responses": [
                    "Здравствуйте! С удовольствием расскажу о наших тарифах",
                    "Привет! Да, у нас есть специальное предложение для новых клиентов",
                    "Добрый день! Базовый тариф подойдет, если вам нужно...",
                    "Здравствуйте! Принимаем карты, PayPal и криптовалюту",
                    "Привет! Отправлю вам презентацию с деталями",
                    "Добрый день! Вот наши актуальные цены...",
                    "Здравствуйте! Могу предложить тестовый период на 7 дней"
                ],
                "conversions": [
                    "Отлично, оформляю заказ!",
                    "Супер, беру! Как оплатить?",
                    "Понятно, давайте оформим",
                    "Хорошо, я согласен. Куда платить?",
                    "Отлично, мне подходит. Оформляем!"
                ]
            },
            "docs": {
                "customer_questions": [
                    "Где найти документацию по API?",
                    "Есть ли примеры интеграции?",
                    "Подскажите, как настроить webhook?",
                    "Где посмотреть список методов API?",
                    "Есть ли у вас SDK для Python?",
                    "Как получить API ключ?",
                    "Нужна инструкция по быстрому старту"
                ],
                "support_responses": [
                    "Вот ссылка на документацию: docs.example.com/api",
                    "Да, есть примеры на GitHub: github.com/example/examples",
                    "Webhook настраивается в разделе Settings → Integrations",
                    "Полный список методов здесь: docs.example.com/methods",
                    "Да, установить можно через pip install example-sdk",
                    "API ключ можно сгенерировать в личном кабинете",
                    "Отправил вам quick start guide на почту"
                ],
                "acknowledgments": [
                    "Спасибо, нашел!",
                    "Отлично, разберусь. Благодарю!",
                    "Понятно, спасибо за ссылки",
                    "Супер, все нашел. Спасибо!",
                    "Отлично, буду изучать. Спасибо!"
                ]
            },
            "refund": {
                "customer_complaints": [
                    "Здравствуйте, хочу вернуть деньги",
                    "Привет, не подошел ваш сервис. Возврат возможен?",
                    "Добрый день, оформите пожалуйста возврат",
                    "Здравствуйте, продукт не соответствует описанию",
                    "Привет, не работает как ожидал. Верните деньги",
                    "Добрый день, передумал. Можно вернуть оплату?"
                ],
                "support_responses": [
                    "Здравствуйте. Конечно, оформим возврат. По какой причине?",
                    "Привет. Жаль, что не подошло. Возврат делаем за 3-5 дней",
                    "Добрый день. Понял. Оформляю возврат прямо сейчас",
                    "Здравствуйте. Извините за неудобства. Сейчас верну средства",
                    "Привет. Хорошо, начинаю процедуру возврата",
                    "Добрый день. Без проблем. На какую карту вернуть?"
                ],
                "resolutions": [
                    "Спасибо за понимание",
                    "Хорошо, жду возврата",
                    "Понятно, благодарю",
                    "Отлично, спасибо за оперативность",
                    "Ок, буду ждать средства"
                ]
            },
            "billing": {
                "customer_questions": [
                    "Здравствуйте, не прошел платеж",
                    "Привет, почему списалось дважды?",
                    "Добрый день, когда спишется оплата?",
                    "Здравствуйте, можно изменить способ оплаты?",
                    "Привет, нужен счет на оплату",
                    "Добрый день, как отключить автоплатеж?",
                    "Здравствуйте, хочу продлить подписку"
                ],
                "support_responses": [
                    "Здравствуйте. Проверю ваш платеж. Какая сумма?",
                    "Привет. Сейчас проверю транзакции. Номер заказа?",
                    "Добрый день. Оплата спишется в день продления",
                    "Здравствуйте. Да, можно изменить в настройках аккаунта",
                    "Привет. Выставляю счет. На какой email отправить?",
                    "Добрый день. Автоплатеж отключается в Billing Settings",
                    "Здравствуйте. Отлично! Какой тариф интересует?"
                ],
                "resolutions": [
                    "Спасибо, платеж прошел!",
                    "Отлично, теперь вижу. Спасибо!",
                    "Понятно, благодарю за разъяснение",
                    "Супер, все настроил. Спасибо!",
                    "Получил счет, оплачу. Спасибо!"
                ]
            }
        }
        
        return templates
    
    def generate_conversation(
        self,
        contact_name: str,
        telegram_username: str,
        conversation_type: str = "random",
        num_exchanges: int = 3
    ) -> List[MessageSimulation]:
        """
        Generate realistic conversation thread.
        
        Args:
            contact_name: Customer name
            telegram_username: Telegram handle
            conversation_type: Type (support/sales/docs/refund/billing/random)
            num_exchanges: Number of back-and-forth exchanges
            
        Returns:
            List of MessageSimulation objects
        """
        self.logger.debug(
            f"Generating {conversation_type} conversation for {contact_name} "
            f"({num_exchanges} exchanges)"
        )
        
        # Select conversation type if random
        if conversation_type == "random":
            conversation_type = random.choice([
                "support", "sales", "docs", "refund", "billing"
            ])
        
        # Map conversation type to tags
        tag_mapping = {
            "support": ContactTag.SUPPORT,
            "sales": ContactTag.SUPPORT,  # Sales inquiries also tagged as support
            "docs": ContactTag.DOCS,
            "refund": ContactTag.REFUND,
            "billing": ContactTag.BILLING
        }
        
        tag = tag_mapping.get(conversation_type, ContactTag.SUPPORT)
        
        # Generate conversation based on type
        if conversation_type == "support":
            return self._generate_support_conversation(num_exchanges, tag)
        elif conversation_type == "sales":
            return self._generate_sales_conversation(num_exchanges, tag)
        elif conversation_type == "docs":
            return self._generate_docs_conversation(num_exchanges, tag)
        elif conversation_type == "refund":
            return self._generate_refund_conversation(num_exchanges, tag)
        elif conversation_type == "billing":
            return self._generate_billing_conversation(num_exchanges, tag)
        else:
            return self._generate_support_conversation(num_exchanges, tag)
    
    def _generate_support_conversation(
        self,
        num_exchanges: int,
        tag: ContactTag
    ) -> List[MessageSimulation]:
        """Generate support inquiry conversation."""
        messages = []
        templates = self.templates["support"]
        
        # Start time (random time in the past week)
        start_time = datetime.now() - timedelta(days=random.randint(1, 7))
        
        # Customer question
        messages.append(MessageSimulation(
            text=random.choice(templates["customer_questions"]),
            timestamp=start_time,
            is_incoming=True,
            message_type="question",
            tags=[tag]
        ))
        
        # Support responses (multiple exchanges)
        for i in range(num_exchanges):
            # Support response
            response_time = start_time + timedelta(minutes=random.randint(5, 30))
            messages.append(MessageSimulation(
                text=random.choice(templates["support_responses"]),
                timestamp=response_time,
                is_incoming=False,
                message_type="response",
                tags=[tag]
            ))
            
            # Customer follow-up (if not last exchange)
            if i < num_exchanges - 1:
                followup_time = response_time + timedelta(minutes=random.randint(10, 60))
                messages.append(MessageSimulation(
                    text=random.choice(templates["customer_questions"]),
                    timestamp=followup_time,
                    is_incoming=True,
                    message_type="question",
                    tags=[tag]
                ))
                start_time = followup_time
        
        # Final resolution
        resolution_time = messages[-1].timestamp + timedelta(minutes=random.randint(5, 20))
        messages.append(MessageSimulation(
            text=random.choice(templates["resolutions"]),
            timestamp=resolution_time,
            is_incoming=True,
            message_type="response",
            tags=[tag]
        ))
        
        return messages
    
    def _generate_sales_conversation(
        self,
        num_exchanges: int,
        tag: ContactTag
    ) -> List[MessageSimulation]:
        """Generate sales inquiry conversation."""
        messages = []
        templates = self.templates["sales"]
        
        start_time = datetime.now() - timedelta(days=random.randint(1, 14))
        
        # Initial inquiry
        messages.append(MessageSimulation(
            text=random.choice(templates["customer_questions"]),
            timestamp=start_time,
            is_incoming=True,
            message_type="question",
            tags=[tag]
        ))
        
        # Sales conversation
        for i in range(num_exchanges):
            response_time = start_time + timedelta(minutes=random.randint(10, 120))
            messages.append(MessageSimulation(
                text=random.choice(templates["support_responses"]),
                timestamp=response_time,
                is_incoming=False,
                message_type="response",
                tags=[tag]
            ))
            
            if i < num_exchanges - 1:
                followup_time = response_time + timedelta(minutes=random.randint(30, 180))
                messages.append(MessageSimulation(
                    text=random.choice(templates["customer_questions"]),
                    timestamp=followup_time,
                    is_incoming=True,
                    message_type="question",
                    tags=[tag]
                ))
                start_time = followup_time
        
        # Conversion
        conversion_time = messages[-1].timestamp + timedelta(hours=random.randint(1, 24))
        messages.append(MessageSimulation(
            text=random.choice(templates["conversions"]),
            timestamp=conversion_time,
            is_incoming=True,
            message_type="order",
            tags=[tag]
        ))
        
        return messages
    
    def _generate_docs_conversation(
        self,
        num_exchanges: int,
        tag: ContactTag
    ) -> List[MessageSimulation]:
        """Generate documentation inquiry conversation."""
        messages = []
        templates = self.templates["docs"]
        
        start_time = datetime.now() - timedelta(days=random.randint(1, 5))
        
        # Question about docs
        messages.append(MessageSimulation(
            text=random.choice(templates["customer_questions"]),
            timestamp=start_time,
            is_incoming=True,
            message_type="question",
            tags=[tag]
        ))
        
        # Quick responses (docs questions are usually resolved faster)
        for i in range(min(num_exchanges, 2)):
            response_time = start_time + timedelta(minutes=random.randint(2, 15))
            messages.append(MessageSimulation(
                text=random.choice(templates["support_responses"]),
                timestamp=response_time,
                is_incoming=False,
                message_type="response",
                tags=[tag]
            ))
            start_time = response_time
        
        # Acknowledgment
        ack_time = messages[-1].timestamp + timedelta(minutes=random.randint(5, 30))
        messages.append(MessageSimulation(
            text=random.choice(templates["acknowledgments"]),
            timestamp=ack_time,
            is_incoming=True,
            message_type="response",
            tags=[tag]
        ))
        
        return messages
    
    def _generate_refund_conversation(
        self,
        num_exchanges: int,
        tag: ContactTag
    ) -> List[MessageSimulation]:
        """Generate refund request conversation."""
        messages = []
        templates = self.templates["refund"]
        
        start_time = datetime.now() - timedelta(days=random.randint(1, 3))
        
        # Refund request
        messages.append(MessageSimulation(
            text=random.choice(templates["customer_complaints"]),
            timestamp=start_time,
            is_incoming=True,
            message_type="complaint",
            tags=[tag]
        ))
        
        # Support handles refund
        response_time = start_time + timedelta(minutes=random.randint(15, 60))
        messages.append(MessageSimulation(
            text=random.choice(templates["support_responses"]),
            timestamp=response_time,
            is_incoming=False,
            message_type="response",
            tags=[tag]
        ))
        
        # Resolution
        resolution_time = response_time + timedelta(minutes=random.randint(10, 30))
        messages.append(MessageSimulation(
            text=random.choice(templates["resolutions"]),
            timestamp=resolution_time,
            is_incoming=True,
            message_type="response",
            tags=[tag]
        ))
        
        return messages
    
    def _generate_billing_conversation(
        self,
        num_exchanges: int,
        tag: ContactTag
    ) -> List[MessageSimulation]:
        """Generate billing inquiry conversation."""
        messages = []
        templates = self.templates["billing"]
        
        start_time = datetime.now() - timedelta(days=random.randint(1, 5))
        
        # Billing question
        messages.append(MessageSimulation(
            text=random.choice(templates["customer_questions"]),
            timestamp=start_time,
            is_incoming=True,
            message_type="question",
            tags=[tag]
        ))
        
        # Support response
        for i in range(min(num_exchanges, 2)):
            response_time = start_time + timedelta(minutes=random.randint(5, 30))
            messages.append(MessageSimulation(
                text=random.choice(templates["support_responses"]),
                timestamp=response_time,
                is_incoming=False,
                message_type="response",
                tags=[tag]
            ))
            start_time = response_time
        
        # Resolution
        resolution_time = messages[-1].timestamp + timedelta(minutes=random.randint(10, 60))
        messages.append(MessageSimulation(
            text=random.choice(templates["resolutions"]),
            timestamp=resolution_time,
            is_incoming=True,
            message_type="response",
            tags=[tag]
        ))
        
        return messages
