import copy
import json
import tempfile
import unittest
from pathlib import Path

from lxml import html

from ginkgo.convert import convert_md_to_json
from ginkgo.core import exam_html_generator, sidebar_html_generator


class MarkdownConversionTests(unittest.TestCase):
    def test_mcqs_and_flashcards_are_converted_from_separate_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exam_path = Path(temp_dir) / 'exam.md'
            exam_path.write_text(
                '''---
title: Section test
author: Tester
description: A test
---

## mcqs

- MCQ question
  - [x] Correct option
  - Incorrect option

## flashcards

- Flashcard question
  - Flashcard answer
''',
                encoding='utf-8',
            )

            exam = json.loads(convert_md_to_json(exam_path))

        self.assertEqual(1, len(exam['mcqs']['questions']))
        self.assertEqual('MCQ question', exam['mcqs']['questions'][0]['q'])
        self.assertEqual(1, len(exam['flashcards']['questions']))
        self.assertEqual(
            {'q': 'Flashcard question', 'a': 'Flashcard answer'},
            exam['flashcards']['questions'][0],
        )

    def test_markdown_images_are_preserved_as_rich_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exam_path = Path(temp_dir) / 'exam.md'
            exam_path.write_text(
                '''---
title: Image test
author: Tester
description: A test
---

## mcqs

- Identify this structure. ![Cell diagram](./images/cell.png "Figure 1")
  - [x] Cell ![Answer detail](https://example.com/answer.png)
  - Tissue
''',
                encoding='utf-8',
            )

            exam = json.loads(convert_md_to_json(exam_path))

        question = exam['mcqs']['questions'][0]
        self.assertEqual('Identify this structure.', question['q']['text'])
        self.assertEqual(
            {
                'src': './images/cell.png',
                'alt': 'Cell diagram',
                'caption': 'Figure 1',
            },
            question['q']['images'][0],
        )
        self.assertEqual('Cell', question['a'][0]['text'])
        self.assertEqual(
            'https://example.com/answer.png',
            question['a'][0]['images'][0]['src'],
        )
        self.assertEqual([0], question['c'])


class ImageBuildTests(unittest.TestCase):
    def test_json_image_shorthand_is_copied_and_rewritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / 'source'
            image_dir = source_dir / 'images'
            image_dir.mkdir(parents=True)
            (image_dir / 'diagram.png').write_bytes(b'fake png contents')

            exam_path = source_dir / 'exam.json'
            exam_path.write_text(
                json.dumps(
                    {
                        'title': 'Image test',
                        'author': 'Tester',
                        'description': 'A test',
                        'mcqs': {
                            'description': '',
                            'questions': [
                                {
                                    'q': {
                                        'text': 'Question',
                                        'image': 'images/diagram.png',
                                    },
                                    'a': ['Correct', 'Incorrect'],
                                    'c': 0,
                                }
                            ],
                        },
                        'flashcards': None,
                    }
                ),
                encoding='utf-8',
            )

            website = {'title': 'Test site'}
            nav = [{'Category': [{'Quiz': str(exam_path)}]}]
            sidebar = sidebar_html_generator(website, nav)
            output_path = root / 'site' / 'Category' / 'Quiz.html'
            assets_dir = root / 'site' / 'assets'
            output_path.parent.mkdir(parents=True)

            page = exam_html_generator(
                website=website,
                filepath=exam_path,
                siderbar_html=copy.deepcopy(sidebar),
                output_path=output_path,
                assets_dir=assets_dir,
            )
            rendered = html.tostring(page, encoding='unicode', method='html')
            copied_images = list(assets_dir.iterdir())

        self.assertEqual(1, len(copied_images))
        self.assertRegex(copied_images[0].name, r'^diagram-[0-9a-f]{12}\.png$')
        self.assertIn('../assets/diagram-', rendered)
        self.assertNotIn('images/diagram.png', rendered)
        self.assertIn('<RichContent value={mcqs[currentIdx].q}', rendered)

    def test_remote_image_url_is_not_copied(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            exam_path = root / 'exam.json'
            remote_url = 'https://example.com/diagram.png'
            exam_path.write_text(
                json.dumps(
                    {
                        'title': 'Remote image test',
                        'author': 'Tester',
                        'description': 'A test',
                        'mcqs': None,
                        'flashcards': {
                            'description': '',
                            'questions': [
                                {
                                    'q': {'text': 'Question', 'image': remote_url},
                                    'a': 'Answer',
                                }
                            ],
                        },
                    }
                ),
                encoding='utf-8',
            )

            website = {'title': 'Test site'}
            sidebar = sidebar_html_generator(website, [])
            output_path = root / 'site' / 'Category' / 'Quiz.html'
            page = exam_html_generator(
                website=website,
                filepath=exam_path,
                siderbar_html=sidebar,
                output_path=output_path,
                assets_dir=root / 'site' / 'assets',
            )
            rendered = html.tostring(page, encoding='unicode', method='html')

        self.assertIn(remote_url, rendered)
        self.assertFalse((root / 'site' / 'assets').exists())


if __name__ == '__main__':
    unittest.main()
