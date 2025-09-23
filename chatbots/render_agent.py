import os
from jinja2 import Environment, FileSystemLoader

def render_template(template_name, context):
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TEMPLATE_PATH = os.path.join(BASE_DIR, "chatbots/templates")
    env = Environment(loader=FileSystemLoader(TEMPLATE_PATH))
    template = env.get_template(template_name)

    return template.render(context)
