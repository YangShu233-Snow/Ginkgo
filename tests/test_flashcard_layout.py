import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = PROJECT_ROOT / 'src' / 'ginkgo' / 'templates' / 'base.html'
QUIZ_TEMPLATE = PROJECT_ROOT / 'src' / 'ginkgo' / 'templates' / 'quiz.html'


class FlashcardLayoutTest(unittest.TestCase):
    def test_card_height_uses_a_viewport_aware_range(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')

        self.assertIn(
            'min-height: clamp(28rem, calc(100dvh - 18rem), 52rem);',
            template,
        )
        self.assertNotIn('height: clamp(320px, 55dvh, 380px);', template)

    def test_card_faces_share_an_intrinsic_grid_layer(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')

        self.assertIn('display: grid;', template)
        self.assertIn('grid-area: 1 / 1;', template)
        self.assertIn('min-height: inherit;', template)

    def test_question_has_no_nested_vertical_scroll_container(self):
        template = QUIZ_TEMPLATE.read_text(encoding='utf-8')
        flashcard = template.split('if (view === "flashcard")', 1)[1]
        card_markup = flashcard.split('{/* 控制按钮 */}', 1)[0]

        self.assertNotIn('overflow-y-auto', card_markup)
        self.assertIn('text-left', card_markup)
        self.assertIn('flip-card-hint', card_markup)
        self.assertIn('<Lightbulb size={22}', card_markup)
        self.assertIn('QUESTION {currentIdx + 1}', card_markup)

    def test_card_supports_keyboard_reveal(self):
        template = QUIZ_TEMPLATE.read_text(encoding='utf-8')

        self.assertIn('role="button"', template)
        self.assertIn('event.key === "Enter" || event.key === " "', template)
        self.assertIn('aria-label={flipped ?', template)

    def test_study_views_support_arrow_key_navigation(self):
        template = QUIZ_TEMPLATE.read_text(encoding='utf-8')

        self.assertIn('event.key === "ArrowLeft"', template)
        self.assertIn('event.key === "ArrowRight"', template)
        self.assertIn(
            'window.addEventListener("keydown", handleKeyDown);',
            template,
        )
        self.assertIn(
            'window.removeEventListener("keydown", handleKeyDown);',
            template,
        )

    def test_arrow_navigation_uses_shared_bounded_functions(self):
        template = QUIZ_TEMPLATE.read_text(encoding='utf-8')

        self.assertIn('const goToPreviousQuestion = useCallback(', template)
        self.assertIn('const goToNextQuestion = useCallback(', template)
        self.assertIn(
            'if (currentIdx >= questionCount - 1) return false;',
            template,
        )
        self.assertEqual(
            template.count('onClick={goToPreviousQuestion}'),
            2,
        )
        self.assertEqual(template.count('onClick={handleNextButton}'), 2)

    def test_reduced_motion_does_not_remove_the_card_flip(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')
        reduced_motion = template.split(
            '@media (prefers-reduced-motion: reduce)',
            1,
        )[1]

        self.assertNotIn('.flip-card-inner', reduced_motion)

    def test_app_height_has_an_explicit_dynamic_viewport_fallback(self):
        template = BASE_TEMPLATE.read_text(encoding='utf-8')

        self.assertIn('.app-viewport {', template)
        self.assertIn('height: 100vh;', template)
        self.assertIn('@supports (height: 100dvh)', template)
        self.assertIn('height: 100dvh;', template)
        self.assertNotIn('h-screen h-[100dvh]', template)

    def test_short_landscape_layout_reserves_safe_scroll_space(self):
        base_template = BASE_TEMPLATE.read_text(encoding='utf-8')
        quiz_template = QUIZ_TEMPLATE.read_text(encoding='utf-8')

        self.assertIn(
            '@media (min-width: 768px) and (max-height: 820px) '
            'and (orientation: landscape)',
            base_template,
        )
        self.assertIn('safe-area-inset-bottom', base_template)
        self.assertIn('scroll-padding-bottom', base_template)
        self.assertIn('app-main', base_template)
        self.assertEqual(quiz_template.count('study-view-controls'), 2)


if __name__ == '__main__':
    unittest.main()
