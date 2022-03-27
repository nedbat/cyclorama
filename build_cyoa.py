from dataclasses import dataclass, field
from pathlib import Path

import jinja2


@dataclass
class Choice:
    var: str
    label: str
    # choices is a list of (text, value).
    choices: list[tuple[str, str]] = field(default_factory=list)


LETTERS = "abcdefghijklmnopqrstuvwxyz"

class CyoaRenderer:
    def __init__(self, src_dir, dst_dir):
        self.src_dir = src_dir
        self.dst_dir = Path(dst_dir)
        self.choices: dict[str, Choice] = {}
        if not self.dst_dir.exists():
            self.dst_dir.mkdir(parents=True)
        self.jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(self.src_dir))

    def render_page(self, page_name, current_choices):
        cpr = CyoaPageRenderer(page_name, current_choices, self)
        cpr.render_page()

    def render_pages(self, start_page):
        todo = [(start_page, {})]
        while todo:
            page_name, current_choices = todo.pop()
            cpr = CyoaPageRenderer(page_name, current_choices, self)
            cpr.render_page()
            todo.extend(cpr.next_pages)

    def choices_slug(self, choices):
        slug = ""
        for var, choice in self.choices.items():
            val = choices.get(var)
            for letter, (_, value) in zip(LETTERS, choice.choices):
                if value == val:
                    slug += letter
                    break
        return slug

    def page_name_with_choices(self, page, choices):
        slug = self.choices_slug(choices)
        if slug:
            page = page.replace(".md", f"_{slug}.md")
        return page


class CyoaPageRenderer:
    def __init__(self, page_name, current_choices, renderer):
        self.page_name = page_name
        self.current_choices = current_choices
        self.renderer = renderer
        self.next_pages = []

    def render_page(self):
        template = self.renderer.jenv.get_template(self.page_name + ".j2")
        vars = {}
        vars.update(
            {m[2:]: getattr(self, m) for m in dir(self.__class__) if m[:2] == "j_"}
        )
        vars.update(self.current_choices)
        md = template.render(vars)
        out_page = self.renderer.page_name_with_choices(self.page_name, self.current_choices)
        with open(self.renderer.dst_dir / out_page, "w", encoding="utf-8") as f:
            f.write(md)
            f.write("\n\n\n\n<br><br><br>\n------\n")
            f.write("Choices that lead here:\n")
            for var, choice in self.renderer.choices.items():
                val = self.current_choices.get(var)
                f.write(f"- {choice.label}:")
                for text, value in choice.choices:
                    if val == value:
                        f.write(f" **{text}**")
                    else:
                        alt_choices = {**self.current_choices, var: value}
                        alt_page = self.renderer.page_name_with_choices(self.page_name, alt_choices)
                        f.write(f" [{text}]({alt_page})")
                f.write("\n")

        print(f"Wrote {out_page}")

    def link_with_choices(self, text, next_page, choices):
        self.next_pages.append((next_page, choices))
        page_name = self.renderer.page_name_with_choices(next_page, choices)
        return f"[{text}]({page_name})"

    # Methods named j_* become Jinja globals.
    def j_choice(self, label, var):
        self.renderer.choices[var] = Choice(var=var, label=label)
        assert var not in self.current_choices
        self.current_choices[var] = None
        return ""

    def j_choose(self, var, text, next_page, value=None):
        assert self.current_choices[var] is None
        if value is None:
            value = text
        self.renderer.choices[var].choices.append((text, value))
        next_choices = {**self.current_choices, var: value}
        return self.link_with_choices(text, next_page, next_choices)

    def j_link(self, text, next_page):
        return self.link_with_choices(text, next_page, self.current_choices)


renderer = CyoaRenderer("src", "docs")
renderer.render_pages("index.md")
