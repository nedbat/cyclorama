from pathlib import Path

import jinja2


class CyoaRenderer:
    def __init__(self, src_dir, dst_dir):
        self.dst_dir = Path(dst_dir)
        if not self.dst_dir.exists():
            self.dst_dir.mkdir(parents=True)
        self.jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(src_dir))

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


def choices_slug(choices):
    return "".join(
        sorted(slug + value for slug, value in choices.items() if value is not None)
    )


def page_name_with_choices(page, choices):
    slug = choices_slug(choices)
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
        md = template.render(
            {m[2:]: getattr(self, m) for m in dir(self.__class__) if m[:2] == "j_"}
        )
        out_page = page_name_with_choices(self.page_name, self.current_choices)
        with open(self.renderer.dst_dir / out_page, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote {out_page}")

    def link_with_choices(self, text, next_page, choices):
        self.next_pages.append((next_page, choices))
        return f"[{text}]({page_name_with_choices(next_page, choices)})"

    # Methods named j_* become Jinja globals.
    def j_choice(self, label, slug):
        assert len(slug) == 1
        assert slug not in self.current_choices
        self.current_choices[slug] = None
        return ""

    def j_choose(self, text, next_page, slug, value):
        assert self.current_choices[slug] is None
        next_choices = {**self.current_choices, slug: value}
        return self.link_with_choices(text, next_page, next_choices)

    def j_chose(self, slug, value):
        return self.current_choices[slug] == value

    def j_link(self, text, next_page):
        return self.link_with_choices(text, next_page, self.current_choices)


renderer = CyoaRenderer("src", "md")
renderer.render_pages("start.md")
