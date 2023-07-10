import copy
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import click
import jinja2

# It's too easy to use the word "choice" for everything, so in the code:
# A decision point for the user is a *question*.  The choices for a question
# are *options*.   The options the user has chosen are *picks*.


def exc_summary(exc):
    """Return a one-line summary of an exception."""
    return "".join(traceback.format_exception_only(exc)).strip()

@dataclass
class Question:
    var: str
    text: str
    # options maps value to text.
    options: dict[str, str] = field(default_factory=dict)


class Renderer:
    def __init__(self, src_dir, dst_dir):
        self.src_dir = src_dir
        self.dst_dir = Path(dst_dir)
        self.questions: dict[str, Question] = {}
        if not self.dst_dir.exists():
            self.dst_dir.mkdir(parents=True)
        self.jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(self.src_dir))
        self.work = None

        # Map page names to the variables used on each page.
        self.page_vars: dict[str, set[str]] = {}
        # Map page names to the pages that link to them.
        self.page_links: dict[str, set[str]] = {}
        # Map page names to the question variable set on the page.
        self.page_questions: dict[str, str] = {}

    def _render_all_pages(self, start_page, renderer_class):
        self.work = [(start_page, {})]
        while self.work:
            page_name, picks = self.work.pop()
            try:
                renderer_class(page_name, picks, self).render_page()
            except Exception as exc:
                print(f"Couldn't render {page_name}: {exc_summary(exc)}")

    def render_pages(self, start_page):
        self._render_all_pages(start_page, PageAnalyzer)

        while True:
            old_page_vars = copy.deepcopy(self.page_vars)
            for page, vars in self.page_vars.items():
                for inbound in self.page_links.get(page, ()):
                    self.page_vars[inbound].update(vars)
                    if inbound in self.page_questions:
                        pq = self.page_questions[inbound]
                        if pq in self.page_vars[inbound]:
                            self.page_vars[inbound].remove(pq)
            if old_page_vars == self.page_vars:
                break

        self._render_all_pages(start_page, PageWriter)

    def add_page_to_render(self, page_name, picks):
        self.work.append((page_name, picks))

    def page_name_with_picks(self, page, picks):
        slug = ""
        page_vars = self.page_vars[page]
        for var, question in self.questions.items():
            if var in page_vars:
                pick = picks.get(var)
                slug += f"_{var}{pick}"
        if slug:
            page = page.replace(".md", f"{slug}.md")
        return page


class TrackingString:
    """A variable for use in Jinja.

    When used as a string ``{{ var }}``, it shows the full text of the user's
    pick.  When use in comparison ``{% if var == "x" %}``, it compares against
    the short value.

    """
    def __init__(self, var, text, value, tracker):
        self.var = var
        self.text = text
        self.value = value
        self.tracker = tracker

    def __str__(self):
        return self.text

    def __eq__(self, other):
        self.tracker.add(self.var)
        return self.value == other

    def __ne__(self, other):
        self.tracker.add(self.var)
        return self.value != other


class BasePageVisitor:
    def __init__(self, page_name, picks, renderer):
        self.page_name = page_name
        self.picks = picks
        self.renderer = renderer

    def render_page(self):
        template = self.renderer.jenv.get_template(self.page_name + ".j2")
        tracker = self.renderer.page_vars.setdefault(self.page_name, set())
        jinja_methods = {
            m[2:]: getattr(self, m)
            for m in dir(self.__class__)
            if m[:2] == "j_"
        }
        variables = {
            var: TrackingString(var, self.renderer.questions[var].options[val], val, tracker)
            for var, val in self.picks.items()
        }
        return template.render({ **jinja_methods, **variables })

    def link_with_picks(self, text, next_page, picks):
        raise NotImplementedError()

    def add_page_to_render(self, next_page, picks):
        self.renderer.add_page_to_render(next_page, picks)

    # Methods named j_* become Jinja globals.

    def j_question(self, text, var):
        """Define a question.

        `text` will be used in breadcrumbs as a short-hand of the question.
        `var` is the name of the Jinja variable that will be defined.

        Values for `var` will be defined with ``option()`` later on the page.
        """
        self.renderer.questions[var] = Question(var=var, text=text)
        self.renderer.page_questions[self.page_name] = var
        assert var not in self.picks
        self.picks[var] = None
        return ""

    def j_option(self, var, text, next_page, value=None):
        """Present an option to question.

        `var` is the variable from a previous ``question()``.
        `text` is the text of the link.
        `next_page` is the .md base name of the page to go to for this option.
        `value` is the value of the variable to set. If not provided, `text` will
        be used.
        """
        assert self.picks[var] is None
        if value is None:
            value = text
        self.renderer.questions[var].options[value] = text
        next_picks = {**self.picks, var: value}
        return self.link_with_picks(text, next_page, next_picks)

    def j_link(self, text, next_page):
        """Generate a link to a page that keeps the current choices.

        `text` is the text that will appear on the current page.
        `next_page` is the base name of the .md file to link to.
        """
        return self.link_with_picks(text, next_page, self.picks)


class PageAnalyzer(BasePageVisitor):
    def link_with_picks(self, text, next_page, picks):
        self.add_page_to_render(next_page, picks)
        self.renderer.page_links.setdefault(next_page, set()).add(self.page_name)
        # While collecting variables, we don't use the markdown, so any text is fine.
        return "LINK GOES HERE"


class PageWriter(BasePageVisitor):
    def render_page(self):
        md = super().render_page()
        out_page = self.renderer.page_name_with_picks(self.page_name, self.picks)
        with open(self.renderer.dst_dir / out_page, "w", encoding="utf-8") as f:
            f.write(md)
            f.write("\n")
            choices = ""
            for var, question in self.renderer.questions.items():
                if var not in self.renderer.page_vars.get(self.page_name, ()):
                    continue
                pick = self.picks.get(var)
                choices += f"- {question.text}:"
                for option, text in question.options.items():
                    if pick == option:
                        choices += f" **{text}**"
                    else:
                        alt_picks = {**self.picks, var: option}
                        alt_page = self.renderer.page_name_with_picks(
                            self.page_name, alt_picks
                        )
                        choices += f" [{text}]({alt_page})"
                choices += "\n"

            if choices:
                f.write("\n\n\n<br><br><br>\n------\n")
                f.write("Choices that lead here:\n")
                f.write(choices)

        print(f"Wrote {out_page}")

    def link_with_picks(self, text, next_page, picks):
        self.add_page_to_render(next_page, picks)
        page_name = self.renderer.page_name_with_picks(next_page, picks)
        return f"[{text}]({page_name})"



@click.group()
def cli():
    pass

@cli.command(help="Render src/START_PAGE.j2 to docs/START_PAGE, and all pages it references")
@click.argument("start_page", type=str, required=True)
def render(start_page):
    renderer = Renderer("src", "docs")
    renderer.render_pages(start_page)


if __name__ == "__main__":
    cli()
