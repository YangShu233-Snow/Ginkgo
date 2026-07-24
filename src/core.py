import copy
import json
import logging
import shutil
import yaml
from lxml import html
from pathlib import Path
from typing import Dict, List, Tuple
from convert import convert_md_to_json

logger = logging.getLogger(__name__)

BASEPATH = Path().cwd()
GINKGO_CONFIG_PATH = BASEPATH / 'ginkgo.yaml'
TEMPLATES_PATH = Path(__file__).parent / 'templates'
BASEHTML_PATH = TEMPLATES_PATH / 'base.html'
SIDEBARHTML_PATH = TEMPLATES_PATH / 'sidebar.html'
INDEXHTML_PATH = TEMPLATES_PATH / 'index.html'
QUIZHTML_PATH = TEMPLATES_PATH / 'quiz.html'

def exam_json_decoder(exam: dict)->Tuple[dict, dict, dict]:
    if not isinstance(exam, dict):
        raise TypeError("The file format isn't correct!")
    
    # v0.0.1 理论上一份卷子的 JSON metadata 需要包含这些数据
    metadata_keys = ['title', 'author', 'description']
    metadata = {}
    
    for metadata_key in metadata_keys:
        if not metadata_key in exam:
            raise ValueError(f"The file loss metadata key: {metadata_key}")
        
        metadata[metadata_key] = exam[metadata_key]

    # 以防万一，排查一下空卷
    mcqs: dict = exam.get('mcqs')
    flashcards: dict = exam.get('flashcards')

    if not (mcqs or flashcards):
        raise ValueError("The file questions is empty!")
    
    mcqs_questions: List[dict] = mcqs.get('questions')
    flashcards_questions: List[dict] = flashcards.get('questions')

    if not (mcqs_questions or flashcards_questions):
        raise ValueError("The file questions is empty!")
    
    # 检查一下 mcqs 和 flashcards 的题目是否符合要求
    # mcqs 每一道题目应当包含 q、a、c；c 可为单个索引，也可为非空索引列表
    for index, mcqs_question in enumerate(mcqs_questions):
        if not isinstance(mcqs_question, dict):
            raise ValueError(f"The mcqs question(No.{index+1}) format is not correct!")
        
        q = mcqs_question.get('q')
        a = mcqs_question.get('a')
        c = mcqs_question.get('c')

        is_single_answer = type(c) is int
        is_answer_list = (
            isinstance(c, list)
            and bool(c)
            and all(type(answer) is int for answer in c)
            and len(c) == len(set(c))
        )
        is_question_format_legal = (
            isinstance(q, str)
            and isinstance(a, list)
            and (is_single_answer or is_answer_list)
        )

        if not is_question_format_legal:
            raise ValueError(f"The mcqs question(No.{index+1}) format is not correct!\nq:{q}\na:{a}\nc:{c}")
        
        correct_answers = [c] if is_single_answer else c
        if any(answer < 0 or answer >= len(a) for answer in correct_answers):
            raise ValueError(f"The mcqs question(No.{index+1}) doesn't have correct answer!")
    
    # flashcards 每道题目应当包含 q, a
    for index, flashcards_question in enumerate(flashcards_questions):
        if not isinstance(flashcards_question, dict):
            raise ValueError(f"The flashcards question(No.{index+1}) format is not correct!")
        
        q = flashcards_question.get('q')
        a = flashcards_question.get('a')

        is_question_format_legal = isinstance(q, str) and isinstance(a, str)

        if not is_question_format_legal:
            raise ValueError(f"The flashcards question(No.{index+1}) format is not correct!\nq:{q}\na:{a}")
        
    return metadata, mcqs, flashcards

def exam_loader(filepath: Path)->Tuple[dict, dict, dict]:
    if not filepath.exists():
        raise IOError(f"{filepath} isn't existing!")
    
    if not filepath.suffix in ['.json', '.md']:
        raise ValueError(f"{filepath} isn't a valid format!")
    
    try:
        if filepath.suffix == '.json':
            with open(filepath, 'r') as f:
                exam: dict = json.load(f)
        else:
            exam = json.loads(convert_md_to_json(filepath=filepath))

        return exam_json_decoder(exam)
    except json.decoder.JSONDecodeError as je:
        logger.error(f"{filepath} isn't a legal json format!")
        raise je
    except Exception as e:
        logger.error(f"A exception occurs!")
        raise e

# 生成 Sidebar HTML，但是暂未高亮
def sidebar_html_generator(website: dict, nav: List[dict]):
    sidebar_html_tree = html.parse(SIDEBARHTML_PATH, html.HTMLParser(encoding='utf-8'))

    link_tpl = sidebar_html_tree.xpath("//*[contains(@class, 'js-tpl-link')]")[0][0]
    category_tpl = sidebar_html_tree.xpath("//*[contains(@class, 'js-tpl-category')]")[0][0]
    menu_container = sidebar_html_tree.xpath("//*[contains(@class, 'js-menu-container')]")[0]

    site_link = sidebar_html_tree.xpath("//*[contains(@class, 'js-site-link')]")[0]
    site_link.set('href', './index.html')
    site_link.text = website['title']

    for cat in nav:
        category, exams = tuple(cat.items())[0]
        new_cat = copy.deepcopy(category_tpl)
        new_cat.xpath(".//*[contains(@class, 'js-category-title')]")[0].text = category
        link_container = new_cat.xpath(".//*[contains(@class, 'js-link-container')]")[0]

        for exam in exams:
            title = tuple(exam.keys())[0]
            href = './' + category + '/' + title + '.html'
            new_link = copy.deepcopy(link_tpl)
            new_link.set('href', href)
            new_link.text = title
            link_container.append(new_link)

        menu_container.append(new_cat)

    return sidebar_html_tree.getroot().find('.//aside')

def rebase_sidebar_links(siderbar_html, prefix: str):
    """按当前页面相对站点根目录的深度调整侧栏链接。"""
    for link in siderbar_html.xpath('.//a[@href]'):
        href = link.get('href')
        if href.startswith('./'):
            link.set('href', prefix + href[2:])

    return siderbar_html

def exam_html_generator(website: dict, filepath: Path|str, siderbar_html):
    try:
        metadata, mcqs, flashcards = exam_loader(filepath=filepath)
    except Exception as e:
        logger.error(e)
        raise

    authors = metadata.get('author')
    if isinstance(authors, list):
        authors = ', '.join(authors)

    quiz_title = metadata.get('title')
    quiz_description = f'<p>{' '.join(metadata.get('description'))}</p>' \
    f'<p>Made by {authors}</p>'

    script_data_content = f'const mcqs = {json.dumps(mcqs.get('questions'), ensure_ascii=False)};\n' \
    f'const flashcards = {json.dumps(flashcards.get('questions'), ensure_ascii=False)};'

    # 初始化题目数据
    quiz_html_tree = html.parse(QUIZHTML_PATH, html.HTMLParser(encoding='utf-8'))
    script_data_node = quiz_html_tree.xpath('//script')[0]
    script_node = quiz_html_tree.xpath('//script')[1]
    script_node.text = script_node.text.replace('<div>title</div>', quiz_title).replace('<div>description</div>', quiz_description)
    script_data_node.text = script_data_content

    # 页面生成
    main_html_tree = html.parse(BASEHTML_PATH, html.HTMLParser(encoding='utf-8'))
    title_node = main_html_tree.xpath('//title')[0]
    asider_container = main_html_tree.xpath("//*[contains(@class, '.js-asider-container')]")[0]
    quiz_container = main_html_tree.xpath("//*[contains(@class, '.js-quiz-container')]")[0]
    title_node.text = website.get('title')
    asider_container.append(siderbar_html)
    quiz_body = quiz_html_tree.find('.//body')
    for child in list(quiz_body):
        quiz_container.append(child)

    return main_html_tree

def index_html_generator(website: dict, nav: List[dict], siderbar_html):
    index_html_tree = html.parse(INDEXHTML_PATH, html.HTMLParser(encoding='utf-8'))
    index_body = index_html_tree.find('.//body')

    site_title = website.get('title')
    category_count = len(nav)
    quiz_count = sum(len(tuple(category.items())[0][1]) for category in nav)

    index_body.xpath("//*[contains(@class, 'js-index-title')]")[0].text = site_title
    index_body.xpath("//*[contains(@class, 'js-index-category-count')]")[0].text = str(category_count)
    index_body.xpath("//*[contains(@class, 'js-index-quiz-count')]")[0].text = str(quiz_count)

    # 首页侧栏标题同时作为当前页面标记。
    site_link = siderbar_html.xpath(".//*[contains(@class, 'js-site-link')]")[0]
    site_link.set('class', 'js-site-link text-blue-600')
    rebase_sidebar_links(siderbar_html, './')

    main_html_tree = html.parse(BASEHTML_PATH, html.HTMLParser(encoding='utf-8'))
    main_html_tree.xpath('//title')[0].text = site_title
    asider_container = main_html_tree.xpath("//*[contains(@class, '.js-asider-container')]")[0]
    page_container = main_html_tree.xpath("//*[contains(@class, '.js-quiz-container')]")[0]
    asider_container.append(siderbar_html)

    for child in list(index_body):
        page_container.append(child)

    return main_html_tree

def nav_walker(website, nav: List[dict], siderbar_html_tpl):
    site_dir = Path(BASEPATH) / 'site'

    if site_dir.exists():
        shutil.rmtree(site_dir)
        
    site_dir.mkdir()

    index_html = index_html_generator(
        website=website,
        nav=nav,
        siderbar_html=copy.deepcopy(siderbar_html_tpl),
    )
    index_path = site_dir / 'index.html'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html.tostring(index_html, encoding='unicode', method='html'))

    for cat in nav:
        category, exams = tuple(cat.items())[0]
        category_dir: Path = site_dir / category

        if not category_dir.exists():
            category_dir.mkdir()

        for exam in exams:
            title, filepath = tuple(exam.items())[0]
            filepath = BASEPATH / filepath
            exam_path: Path = category_dir / f"{title}.html"
            href = './' + category + '/' + title + '.html'

            sidebar_html = copy.deepcopy(siderbar_html_tpl)
            # 高亮对应的 siderbar link
            now_link_node = sidebar_html.xpath(f'//a[@href="{href}"]')[0]
            now_link_node.set('class', 'block w-full text-left px-3 py-1.5 text-xs rounded-md transition-all bg-blue-50 text-blue-600 font-bold')
            # 修复链接跳转问题
            rebase_sidebar_links(sidebar_html, '../')

            try:
                main_html = exam_html_generator(website=website, filepath=filepath, siderbar_html=sidebar_html)
            except Exception as e:
                logger.error(f"An exception occurs! The details: {e}")
                logger.warning(f"The file {filepath} has been skipped.")
                continue

            with open(exam_path, 'w', encoding='utf-8') as f:
                f.write(html.tostring(main_html, encoding='unicode', method='html'))

def main_generator():
    if not GINKGO_CONFIG_PATH.exists():
        logger.error("ginkgo.yaml isn\'t existing!")
        raise IOError("ginkgo.yaml isn\'t existing!")

    with open(GINKGO_CONFIG_PATH, 'r') as f:
        ginkgo_config: dict = yaml.safe_load(f)

    if not isinstance(ginkgo_config, dict):
        logger.error(f"{GINKGO_CONFIG_PATH} isn\'t correct.")
        raise TypeError(f"{GINKGO_CONFIG_PATH} isn\'t correct.")

    website = ginkgo_config.get('website')
    nav = ginkgo_config.get('nav')
    sidebar_html = sidebar_html_generator(website=website, nav=nav)

    nav_walker(website=website, nav=nav, siderbar_html_tpl=sidebar_html)
