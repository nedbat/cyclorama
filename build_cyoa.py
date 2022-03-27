from dataclasses import dataclass, field
from pathlib import Path

import jinja2

# It's too easy to use the word "choice" for everything, so in the code:
# A decision point for the user is a *question*.  The choices for a question
# are called *options*.   The options the user has chosen are called *picks*.


@dataclass
class Question:
    var: str
    text: str
    # options is a list of (text, value).
    options: list[tuple[str, str]] = field(default_factory=list)


LETTERS = "abcdefghijklmnopqrstuvwxyz"


class CyoaRenderer:
    def __init__(self, src_dir, dst_dir):
        self.src_dir = src_dir
        self.dst_dir = Path(dst_dir)
        self.questions: dict[str, Question] = {}
        if not self.dst_dir.exists():
            self.dst_dir.mkdir(parents=True)
        self.jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(self.src_dir))

    def render_pages(self, start_page):
        todo = [(start_page, {})]
        while todo:
            page_name, picks = todo.pop()
            cpr = CyoaPageRenderer(page_name, picks, self)
            cpr.render_page()
            todo.extend(cpr.next_pages)

    def picks_slug(self, picks):
        slug = ""
        for var, question in self.questions.items():
            pick = picks.get(var)
            for letter, (_, option) in zip(LETTERS, question.options):
                if pick == option:
                    slug += letter
                    break
        return slug

    def page_name_with_picks(self, page, picks):
        slug = self.picks_slug(picks)
        if slug:
            page = page.replace(".md", f"_{slug}.md")
        return page


class CyoaPageRenderer:
    def __init__(self, page_name, picks, renderer):
        self.page_name = page_name
        self.picks = picks
        self.renderer = renderer
        self.next_pages = []

    def render_page(self):
        template = self.renderer.jenv.get_template(self.page_name + ".j2")
        vars = {}
        vars.update(
            {m[2:]: getattr(self, m) for m in dir(self.__class__) if m[:2] == "j_"}
        )
        vars.update(self.picks)
        md = template.render(vars)
        out_page = self.renderer.page_name_with_picks(self.page_name, self.picks)
        with open(self.renderer.dst_dir / out_page, "w", encoding="utf-8") as f:
            f.write(md)
            f.write("\n\n\n\n<br><br><br>\n------\n")
            f.write("Choices that lead here:\n")
            for var, question in self.renderer.questions.items():
                pick = self.picks.get(var)
                f.write(f"- {question.text}:")
                for text, option in question.options:
                    if pick == option:
                        f.write(f" **{text}**")
                    else:
                        alt_picks = {**self.picks, var: option}
                        alt_page = self.renderer.page_name_with_picks(
                            self.page_name, alt_picks
                        )
                        f.write(f" [{text}]({alt_page})")
                f.write("\n")

        print(f"Wrote {out_page}")

    def link_with_picks(self, text, next_page, picks):
        self.next_pages.append((next_page, picks))
        page_name = self.renderer.page_name_with_picks(next_page, picks)
        return f"[{text}]({page_name})"

    # Methods named j_* become Jinja globals.
    def j_choice(self, text, var):
        self.renderer.questions[var] = Question(var=var, text=text)
        assert var not in self.picks
        self.picks[var] = None
        return ""

    def j_choose(self, var, text, next_page, value=None):
        assert self.picks[var] is None
        if value is None:
            value = text
        self.renderer.questions[var].options.append((text, value))
        next_picks = {**self.picks, var: value}
        return self.link_with_picks(text, next_page, next_picks)

    def j_link(self, text, next_page):
        return self.link_with_picks(text, next_page, self.picks)


renderer = CyoaRenderer("src", "docs")
renderer.render_pages("index.md")
