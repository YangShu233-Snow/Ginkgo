[Ginkgo Logo](assets/logo.png)

---

# Ginkgo

一个Markdown文档静态网站构建框架，探索历年卷传承的新方式。

## Feature

1. 从特定格式要求的 Ginkgo Markdown 文档开始，自动构建一个可以立即部署于任何服务器上的静态网站框架。
2. 将历年卷题目转化为在线交互的选择题与问答卡，提供更多历年卷传承方式。
3. 快速部署至 Github Pages，让协作传承更简单。

| Ginkgo Markdown 格式名称 | 是否支持 |
| :----------------------: | :------: |
|      题干内图像插入      |    是    |
|   选项或答案内图像插入   |    是    |
|      题干内公式插入      |    是    |
|   选项或答案内公式插入   |    是    |
|      题干内表格插入      |    是    |
|      答案内表格插入      |    是    |
|      选项内表格插入      |    否    |

## Usage

Ginkgo 支持构建、自动发布、本地预览等功能，并提供提示词以帮助使用者借助 LLM 快速将原始资料整理成可使用的 Ginkgo Markdown。

```text
$ ginkgo --help
Usage: ginkgo [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  build
  gh-deploy
  prompt
  serve
```

更多详细内容，请参见 [Usage](docs/Usage.md)。

## Links

看看 Ginkgo 能做成什么！

1. [ZJUBMS Ginkgo](https://yangshu233-snow.github.io/ZJUBMS-Ginkgo/): 基于 Ginkgo 构建的浙江大学基础医学历年卷仓库

## Acknowledgements

感谢以下项目或前辈对 `Ginkgo` 的支持与贡献：

1. [Mkdocs](https://github.com/mkdocs/mkdocs/)：Ginkgo 架构设计与部分功能实现参考了 Mkdocs 的优秀示范

## License

本项目基于 [MIT LICENSE](LICENSE) 开源，Do anything you want to do!
