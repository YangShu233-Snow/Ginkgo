import json
import tempfile
import unittest
from pathlib import Path

from lxml import html

from ginkgo.convert import convert_md_to_json
from ginkgo.core import exam_html_generator, exam_json_decoder, exam_loader


TABLE_MARKDOWN = r'''---
title: Table test
author: Tester
description: Structured content
---

## mcqs

- Before ![Plot](https://example.com/plot.png "Plot") after $x$:

    | Left | Middle | Right |
    |:-----|:------:|------:|
    | $a$  | $b$    | $c$   |

  - [x] First
  - Second
  - ![Image option](https://example.com/option.png)

## flashcards

- Read this table:

    | Name | Value |
    |:-----|------:|
    | A    | 1     |

  - Answer $x^2$

    | Key | Result |
    |:---:|-------:|
    | X   | 2      |
'''


class TableSupportTests(unittest.TestCase):
    def _markdown_path(self, directory):
        path = Path(directory) / 'table.md'
        path.write_text(TABLE_MARKDOWN, encoding='utf-8')
        return path

    def test_converter_preserves_element_order_and_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            result = json.loads(convert_md_to_json(self._markdown_path(directory)))

        mcq = result['mcqs']['questions'][0]
        self.assertEqual(
            [element['type'] for element in mcq['question']],
            ['text', 'image', 'text', 'table'],
        )
        table = mcq['question'][-1]
        self.assertEqual(table['headers'], ['Left', 'Middle', 'Right'])
        self.assertEqual(table['rows'], [['$a$', '$b$', '$c$']])
        self.assertEqual(table['align'], ['left', 'middle', 'right'])
        self.assertEqual(mcq['options'][0]['type'], 'text')
        self.assertNotIn('elements', mcq['options'][0])
        self.assertTrue(mcq['options'][0]['correct'])
        self.assertFalse(mcq['options'][1]['correct'])
        self.assertEqual(mcq['options'][2]['type'], 'image')
        self.assertEqual(mcq['options'][2]['alt'], 'Image option')

        flashcard = result['flashcards']['questions'][0]
        self.assertEqual(
            [element['type'] for element in flashcard['question']],
            ['text', 'table'],
        )
        self.assertEqual(
            [element['type'] for element in flashcard['answer']],
            ['text', 'table'],
        )

    def test_loader_accepts_new_schema_and_normalizes_legacy_json(self):
        with tempfile.TemporaryDirectory() as directory:
            _, mcqs, flashcards = exam_loader(self._markdown_path(directory))

        self.assertEqual(mcqs['questions'][0]['question'][-1]['type'], 'table')
        self.assertEqual(flashcards['questions'][0]['answer'][-1]['type'], 'table')

        legacy_exam = {
            'title': 'Legacy',
            'author': ['Tester'],
            'description': 'Old schema',
            'mcqs': {
                'description': '',
                'questions': [{'q': 'Question', 'a': ['A', 'B'], 'c': 0}],
            },
            'flashcards': None,
        }
        _, legacy_mcqs, _ = exam_json_decoder(legacy_exam)
        question = legacy_mcqs['questions'][0]
        self.assertEqual(question['question'][0]['content'], 'Question')
        self.assertTrue(question['options'][0]['correct'])

    def test_tables_are_rejected_inside_options(self):
        exam = {
            'title': 'Invalid',
            'author': ['Tester'],
            'description': 'Table option',
            'mcqs': {
                'description': '',
                'questions': [{
                    'question': [{'type': 'text', 'content': 'Question'}],
                    'options': [{
                        'type': 'table',
                        'headers': ['A'],
                        'rows': [['B']],
                        'align': ['left'],
                        'correct': True,
                    }],
                }],
            },
            'flashcards': None,
        }
        with self.assertRaises(ValueError):
            exam_json_decoder(exam)

    def test_generated_page_contains_table_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = exam_html_generator(
                {'title': 'Test site'},
                self._markdown_path(directory),
                html.fromstring('<aside></aside>'),
            )
        page = html.tostring(tree, encoding='unicode', method='html')
        self.assertIn('const ContentTable', page)
        self.assertIn('bg-brand-500/50', page)
        self.assertIn('border-slate-300/50', page)
        self.assertIn('"type": "table"', page)


if __name__ == '__main__':
    unittest.main()
