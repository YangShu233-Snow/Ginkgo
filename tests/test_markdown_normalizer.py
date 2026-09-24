import tempfile
import unittest
from pathlib import Path

from ginkgo.core import exam_loader
from ginkgo.markdown_normalizer import GinkgoMarkdownNormalizer


COMPACT_MCQ = r'''---
title: Repro
author: Tester
description: Test
---

## mcqs

- The discrete random variable X has probability function:
  | $x$      | 0    | 1    | 2   | 3   |
  | -------- | ---- | ---- | --- | --- |
  | $P(X=x)$ | $3a$ | $2a$ | $a$ | $b$ |
  - 5a + b = 1 | equivalent form
  - [x] 6a + b = 1
  - 5a + 2b = 1
  - 7a + b = 1
'''


class MarkdownNormalizerTests(unittest.TestCase):
    def test_canonical_table_is_unchanged(self):
        source = (
            '## mcqs\r\n\r\n'
            '- Question:\r\n\r\n'
            '    | A | B |\r\n'
            '    |---|---|\r\n'
            '    | 1 | 2 |\r\n\r\n'
            '  - [x] Yes\r\n'
        )
        state = GinkgoMarkdownNormalizer(source).normalize()
        self.assertFalse(state.changed)
        self.assertEqual(state.normalized_table_count, 0)
        self.assertEqual(state.normalized, source)

    def test_compact_mcq_table_is_normalized_and_loads(self):
        state = GinkgoMarkdownNormalizer(COMPACT_MCQ).normalize()
        self.assertTrue(state.changed)
        self.assertEqual(state.normalized_table_count, 1)
        self.assertIn(
            'function:\n\n    | $x$      |',
            state.normalized,
        )
        self.assertIn(
            '| $P(X=x)$ | $3a$ | $2a$ | $a$ | $b$ |\n\n  - 5a',
            state.normalized,
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'repro.md'
            path.write_text(COMPACT_MCQ, encoding='utf-8')
            _, mcqs, _ = exam_loader(path)

        question = mcqs['questions'][0]
        self.assertEqual(
            [element['type'] for element in question['question']],
            ['text', 'table'],
        )
        self.assertEqual(len(question['options']), 4)
        self.assertFalse(question['options'][0]['correct'])
        self.assertTrue(question['options'][1]['correct'])

    def test_two_space_table_with_existing_blank_line_is_normalized(self):
        source = '''## mcqs

- Question:

  | A | B |
  |---|---|
  | 1 | 2 |
  - [x] Yes
'''
        state = GinkgoMarkdownNormalizer(source).normalize()
        self.assertEqual(state.normalized_table_count, 1)
        self.assertIn('\n    | A | B |', state.normalized)
        self.assertIn('| 1 | 2 |\n\n  - [x] Yes', state.normalized)

    def test_compact_flashcard_question_and_answer_tables_are_normalized(self):
        source = '''---
title: Flashcard
author: Tester
description: Test
---

## flashcards

- Question:
  | A | B |
  |---|---|
  | 1 | 2 |
  - Answer:
    | C | D |
    |---|---|
    | 3 | 4 |
'''
        state = GinkgoMarkdownNormalizer(source).normalize()
        self.assertEqual(state.normalized_table_count, 2)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'flashcard.md'
            path.write_text(source, encoding='utf-8')
            _, _, flashcards = exam_loader(path)

        flashcard = flashcards['questions'][0]
        self.assertEqual(
            [element['type'] for element in flashcard['question']],
            ['text', 'table'],
        )
        self.assertEqual(
            [element['type'] for element in flashcard['answer']],
            ['text', 'table'],
        )

    def test_flashcard_table_continuation_stays_inside_question(self):
        source = '''---
title: Flashcard
author: Tester
description: Test
---

## flashcards

- Suppose you want to test whether smoking is associated with disease.
    |            | Disease | No Disease |
    | ---------- | ------: | ---------: |
    | Smoker     |      60 |         40 |
    | Non-smoker |      30 |         70 |
   Fill the following table and perform a Chi-square test.
     |            | Disease | No Disease |
     | ---------- | ------- | ---------- |
     | Smoker     |         |            |
     | Non-smoker |         |            |
  - Use a Chi-square test and reject the null hypothesis.
'''
        state = GinkgoMarkdownNormalizer(source).normalize()
        self.assertEqual(state.normalized_table_count, 2)
        self.assertEqual(state.normalized_continuation_count, 1)
        self.assertIn(
            '\n    Fill the following table and perform a Chi-square test.\n',
            state.normalized,
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'flashcard.md'
            path.write_text(source, encoding='utf-8')
            _, _, flashcards = exam_loader(path)

        flashcard = flashcards['questions'][0]
        self.assertEqual(
            [element['type'] for element in flashcard['question']],
            ['text', 'table', 'text', 'table'],
        )
        self.assertEqual(
            flashcard['answer'],
            [{'type': 'text', 'content': (
                'Use a Chi-square test and reject the null hypothesis.'
            )}],
        )

    def test_non_table_pipes_and_mcq_option_tables_are_not_rewritten(self):
        source = '''## mcqs

- The symbol A | B is ordinary text.
  - [x] Option
    | A | B |
    |---|---|
    | 1 | 2 |
'''
        state = GinkgoMarkdownNormalizer(source).normalize()
        self.assertFalse(state.changed)
        self.assertEqual(state.normalized_table_count, 0)

        standalone = '''## mcqs

- Question
  - [x] Answer

Standalone paragraph
  | A | B |
  |---|---|
  | 1 | 2 |
'''
        standalone_state = GinkgoMarkdownNormalizer(standalone).normalize()
        self.assertFalse(standalone_state.changed)

        fenced = '''## mcqs

- Question

  ```text
  | A | B |
  |---|---|
  | 1 | 2 |
  ```
  - [x] Answer
'''
        fenced_state = GinkgoMarkdownNormalizer(fenced).normalize()
        self.assertFalse(fenced_state.changed)


if __name__ == '__main__':
    unittest.main()
