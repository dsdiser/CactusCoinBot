from html import unescape
from typing import Literal, List, Optional
from dataclasses import dataclass
import requests

Difficulty = Literal['easy', 'medium', 'hard']
QuestionType = Literal['boolean', 'multiple']


def html_decode(s):
    """
    Returns the ASCII decoded version of the given HTML string. This does
    NOT remove normal HTML tags like <p>.
    """
    return unescape(s)


@dataclass
class Question:
    category: str
    type: QuestionType
    question: str
    correct_answer: str
    incorrect_answers: List[str]

    def get_choices(self) -> List[str]:
        """
        Gets the possible choices for the question in a random order if multiple choice
        :return:
        """
        if self.type == 'boolean':
            choices = self.incorrect_answers + [self.correct_answer]
            # sort so that true is before false
            choices.sort(reverse=True)
            return choices
        else:
            choices = self.incorrect_answers + [self.correct_answer]
            choices.sort()
            return choices

    @staticmethod
    def from_json(json_dict):
        return Question(
            category=json_dict['category'],
            type=json_dict['type'],
            question=html_decode(json_dict['question']),
            correct_answer=html_decode(json_dict['correct_answer']),
            incorrect_answers=[html_decode(a) for a in json_dict['incorrect_answers']]
        )

    def __hash__(self):
        return hash((self.question, self.type))


@dataclass
class TriviaResponse:
    """Class for the response from the trivia API"""
    response_code: int
    results: List[Question]

    @staticmethod
    def from_json(json_dict):
        return TriviaResponse(
            response_code=json_dict['response_code'],
            results=list(map(Question.from_json, json_dict['results']))
        )


def get_trivia_questions(amount: str = '1', category: Optional[str] = None, difficulty: Optional[Difficulty] = None) -> List[Question]:
    """
    Uses https://opentdb.com/api_config.php to fetch a trivia question and converts it to a question object we can use
    :param amount:
    :param category:
    :param difficulty:
    :return:
    """
    request_url = f'https://opentdb.com/api.php?amount={amount}'
    if category:
        request_url = request_url + f'&category={category}'
    if difficulty:
        request_url = request_url + f'&difficulty={difficulty}'
    r = requests.get(request_url)
    response = TriviaResponse.from_json(r.json())
    return response.results
