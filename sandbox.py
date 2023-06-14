"""A sandbox for figuring out how Jinja works."""

import jinja2

template = jinja2.Template("""
    {% set number = 52 %}
    {% set choice = "apple" %}
    Hello {{name}} {{number}}!
    {% if number > 50 %}
        More than 40!
        {% set also = 'foo' %}
    {% endif %}
    """)

ctx = template.new_context(vars = {"name": "Ned"})
print(template.render(ctx).strip())
#print(vars)
print("get_all:", ctx.get_all())
print("exported_vars:", ctx.exported_vars)
print("vars:", ctx.vars)
print("template.module:", dir(template.module))
print(template.module.number)
mod = template.module
template_vars = {n:getattr(mod, n) for n in dir(mod) if not n.startswith("_")}
print(template_vars)


print("han-solo:")

import jinja2

template = jinja2.Template("""
    {% set number = 42 %}
    Hello {{name}} {{number}}!
    """)

vars = {"name": "Ned"}
print(template.render(vars).strip())
print(vars)


from jinja2 import Environment
env = Environment()


from jinja2.runtime import Context
ctx = Context(env, vars, '', template.blocks)
list(template.render(ctx))

print(ctx.vars)
print(ctx.get_all())



print("="*80)
import jinja2

template = jinja2.Template("""
    {% set number = 52 %}
    {% set choice = "apple" %}
    Hello {{name}} {{number}}!
    {% if number > 50 %}
        More than 40!
        {% set also = 'foo' %}
    {% endif %}
    """)

ctx = template.new_context(vars = {"name": "Ned"})
template.render(ctx)
mod = template.module
template_vars = {n:getattr(mod, n) for n in dir(mod) if not n.startswith("_")}
print(template_vars)
