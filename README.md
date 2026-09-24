# Ginkgo

一个Markdown文档静态网站构建框架，探索历年卷传承的新方式。

## Feature

1. 从特定格式要求的 Markdown 文档开始，自动构建一个可以立即部署于任何服务器上的静态网站框架。
2. 将历年卷题目转化为在线交互的选择题与问答卡，提供更多历年卷传承方式。
3. 支持快速部署至 Github Pages，让协作传承更简单。
4. 支持在题目、选项、抽认卡和试卷描述中使用 LaTeX 数学公式。

## LaTeX

生成的页面会通过 CDN 加载 MathJax。Markdown 和 JSON 试卷均可使用 `$...$`
书写行内公式，或使用 `$$...$$` 书写独立公式。例如：

```markdown
- 求函数 $f(x) = x^2 + 2x + 1$ 的最小值。
- $$\int_0^1 x^2\,dx = \frac{1}{3}$$
```

也支持 MathJax 的 `\(...\)` 与 `\[...\]` 分隔符。若正文需要显示普通的美元符号，
请写成 `\$`。

## Links

1. [ZJUBMS Ginkgo](https://yangshu233-snow.github.io/ZJUBMS-Ginkgo/): 基于 Ginkgo 构建的浙江大学基础医学历年卷仓库

## License

本项目基于 [MIT LICENSE](LICENSE) 开源，Do anything you want to do!
