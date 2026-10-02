from iaula.portal.courses import short_name
from iaula.portal.materials import parse_course_page

HTML = """
<ul><li class="section"><h3 class="sectionname">Semana 1</h3>
<ul><li class="activity resource modtype_resource" id="module-42">
<a class="aalink" href="https://x/mod/resource/view.php?id=42">
<span class="instancename">Tema 1 <span class="accesshide">Archivo</span></span></a></li>
<li class="activity assign modtype_assign" id="module-43">
<a class="aalink" href="https://x/mod/assign/view.php?id=43"><span class="instancename">Tarea</span></a></li>
</ul></li></ul>
"""


def test_parse_course_page() -> None:
    items = parse_course_page(HTML, 7)
    assert [(m.id, m.kind, m.title, m.section) for m in items] == [
        (42, "resource", "Tema 1", "Semana 1"),
        (43, "assign", "Tarea", "Semana 1"),
    ]


def test_short_name() -> None:
    n = "A -- INTELIGENCIA DE NEGOCIOS / TECNOLOGÍAS DE LA INFORMACIÓN 2024 -AS--20262-1"
    assert short_name(n) == "Inteligencia De Negocios"
