# Ginkgo 快速上手

## Install

Ginkgo 已发布在 [PyPI](https://pypi.org/project/ginkgo-flashcards/) 上，通过 `pip` 在本地环境中安装。

```bash
pip install ginkgo-flashcards

ginkgo --help
```

## Before Building

在正式开始构建前，需要先在本地组织一个待构建仓库:

```text
ginkgo-project/
├── docs/
│   ├── category-1/
│   │   ├── quizz-1.md
│   │   └── quizz-2.md
│   └── quizz-3.md
├── .gitignore
└── ginkgo.yaml
```

其中，`ginkgo.yaml` 是 Ginkgo 项目的配置文件，Ginkgo 会加载该配置文件来构建网站；`docs/` 为文档入口，为 Ginkgo 在 `ginkgo serve` 下默认监听的文档入口。

`.gitignore` 并不是必须的，但我依然推荐以 Git 仓库的形式来管理你的 Ginkgo 网站项目。

### ginkgo.yaml

`ginkgo.yaml` 最简示例如下:

```yaml
website:
  title: 'My Ginkgo Website'

nav:
  - Category 1:
    - Quizz 1: docs/category-1/quizz-1.md
    - Quizz 2: docs/category-1/quizz-2.md
  - Other:
    - Quizz 3: docs/quizz-3.md
```

其中 `website` 配置项主要为网站总体配置，目前支持 `title` 字段设置网站大标题。

`nav` 为网站结构描述，目前 Ginkgo 要求每份文档都必须被包含在一个一级分类下。

实际生成的网站结构依照 `nav` 的键名从属关系，而并非 `docs/` 文档内部文件结构。但仍然建议在一定程度上保持 `docs/` 目录结构和 `nav` 配置的网站结构相似。

### docs

一般在 `docs/` 内存放待构建的 Markdown 文档，有关于 Ginkgo Markdown 的相关格式要求，请阅读 [Ginkgo Markdown](./Ginkgo.md)

### Work with LLM

通过以下命令，Ginkgo 会提供其内置的 Prompt，该 Prompt 可以基本指导 LLM 将不同格式的资源转化为一份 Ginkgo Markdown。

```bash
# 将一份已经为历年卷（特别是 Markdown）转化为一份 Ginkgo Markdown
ginkgo prompt --memory

# 将一份资料尝试转化为 Ginkgo Markdown
ginkgo prompt --standard
```

## Build and Deploy

当你完成最基本的配置和文档撰写后，就可以开始通过 Ginkgo 构建网站了，所有构建均需要在 `ginkgo.yaml` 同级目录下（即项目根目录下）完成。

Ginkgo 提供三种相关模式。

### Only Build

通过以下命令，直接从文档开始构建 Ginkgo Website，构建产物生成在 `site/` 下。

```bash
ginkgo build
```

`site/` 包含 Ginkgo 生成的完整静态网站文件。

### Livereload

通过以下命令，Ginkgo 可以提供本地预览的功能，默认本地地址为 `http://127.0.0.1:7777`。

```bash
ginkgo serve
```

Ginkgo 会自动监听 `docs/` 文档下的文件变化，并实时刷新在浏览器内。

### Github Page Deploy

如果项目仓库为 Git 仓库，且关联了远程仓库，通过以下命令，Ginkgo 会自动构建并推送构建的网页至远程仓库上的 `gh-pages` 分支。

```bash
ginkgo gh-deploy
```

通过 Github Page 等功能，可以从分支上实现网页的部署与发布。