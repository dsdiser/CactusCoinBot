from typing import Literal, List
from dataclasses import dataclass
from random import shuffle
import requests

Difficulty = Literal['easy', 'medium', 'hard']
QuestionType = Literal['boolean', 'multiple']


def html_decode(s):
    """
    Returns the ASCII decoded version of the given HTML string. This does
    NOT remove normal HTML tags like <p>.
    """
    htmlCodes = (
            ('\'', '&#039;'),
            ('', '&quot;'),
            ('>', '&gt;'),
            ('<', '&lt;'),
            ('&', '&amp;')
        )
    for code in htmlCodes:
        s = s.replace(code[1], code[0])
    return s


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
            return ['True', 'False']
        else:
            choices = self.incorrect_answers + [self.correct_answer]
            shuffle(choices)
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


def get_trivia_question(category: str = '15', difficulty: Difficulty = 'easy') -> Question:
    """
    Uses https://opentdb.com/api_config.php to fetch a trivia question and converts it to a question object we can use
    :param category:
    :param difficulty:
    :return:
    """
    r = requests.get(f'https://opentdb.com/api.php?amount=1&category={category}&difficulty={difficulty}')
    response = TriviaResponse.from_json(r.json())
    return response.results[0]
