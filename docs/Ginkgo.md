# Ginkgo Markdown 格式指南

Ginkgo Markdown 是 Ginkgo 所接受的，用于构建网站的 Markdown 格式，平衡了格式化文档与便于人类阅读、编写两方面要求。

> 或许吧……

一个最简单的 Ginkgo Markdown 示例如下:

```markdown
---
title: Example Quizz
author: Yangshu233
description: This is an example for tutorial.
---

## mcqs

- A example question:
  - Option A
  - [x] Option B(Correct One)

---

- Another example question as multi-options:
  - [x] Option A (Correct One)
  - [x] Option B (Correct One)
  - Option C

## flashcards

- A question have a loooong text.
  - A loooong text as an answer.
```

## Before Starting

如果你发现按照如下指导无法解决你遇到的格式问题（如 Ginkgo 爆出格式错误，提示需要同时提供题目与答案等等），请 **大胆加缩进**！！！

如果你认为这种格式错误是一个 Bug，请在项目下提 Issue。

## Metadata

Ginkgo Markdown 要求文档内提供三种元数据：`title`、`author` 与 `description`，三者值可以为空。

## mcqs

`mcqs` 是用作构建选择题型的分类，隶属于该二级标题下的题目数据会被认为是选择题。

选择题支持单选题或多选题，通过 `[x]` 标定正确答案，而单选或多选由 Ginkgo 自动识别决定。

所有 mcqs 题目之间需要以 `\n---\n\n` 来分割，即：

```markdown

---

```

## flashcards

`flashcards` 是用作构建闪卡/抽认卡题型的分类，隶属于该二级标题下的题目数据会被认为是问答题。

问答题中一级列表被认为是题干，二级列表被认为是答案。

所有 flashcards 题目之间需要以 `\n---\n\n` 来分割，即：

```markdown

---

```

## More Syntax

Ginkgo Markdown 支持 LaTeX 公式、表格、图片的插入。

| Ginkgo Markdown 格式名称 | 是否支持 |
| :----------------------: | :------: |
|      题干内图像插入      |    是    |
|   选项或答案内图像插入   |    是    |
|      题干内公式插入      |    是    |
|   选项或答案内公式插入   |    是    |
|      题干内表格插入      |    是    |
|      答案内表格插入      |    是    |
|      选项内表格插入      |    否    |

其中图片、公式均支持行内插入。语法与一般 Markdown 没有区别。

如果需要行间插入，其务必不要吝啬你的换行回车与缩进。

例如:

```markdown
- The discrete random variable X has probability function:
  $$P(X=x)=\begin{cases}a(3-x), & x=0,1,2,\\b, & x=3.\end{cases}$$
  |   $x$    |   0   |   1   |   2   |   3   |
  | :------: | :---: | :---: | :---: | :---: |
  | $P(X=x)$ | $3a$  | $2a$  |  $a$  |  $b$  |
  - 5a + b = 1
  - [x] 6a + b = 1
  - 5a + 2b = 1
  - 7a + b = 1
```