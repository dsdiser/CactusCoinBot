import random


def random_id():
    """
    Gets random line from the list of possible ids
    :return: A random line from the file
    """
    with open('list_of_four_letter_words.txt') as file:
        line = next(file)
        for num, aline in enumerate(file, 2):
            if random.randrange(num):
                continue
            line = aline
        return line
