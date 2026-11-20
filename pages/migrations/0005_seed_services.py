from django.db import migrations

# The services the page launched with, in Catalan, Spanish and English
INITIAL = [
    (
        {'ca': 'Branding i Identitat', 'es': 'Branding e Identidad', 'en': 'Branding & Identity'},
        [
            (
                {'ca': 'Identitat visual essencial', 'es': 'Identidad visual esencial', 'en': 'Essential visual identity'},
                {
                    'ca': "Logotip principal, paleta de colors, combinació tipogràfica i guia d'aplicació en PDF.",
                    'es': 'Logotipo principal, paleta de colores, combinación tipográfica y guía de aplicación en PDF.',
                    'en': 'Main logo, colour palette, typeface pairing and a PDF usage guide.',
                },
            ),
            (
                {'ca': 'Sistema de marca complet', 'es': 'Sistema de marca completo', 'en': 'Complete brand system'},
                {
                    'ca': 'Univers gràfic integral, variants de logotip, manual, papereria i plantilles digitals.',
                    'es': 'Universo gráfico integral, variantes de logotipo, manual, papelería y plantillas digitales.',
                    'en': 'A complete visual world: logo variants, brand manual, stationery and digital templates.',
                },
            ),
        ],
    ),
    (
        {'ca': 'Il·lustració', 'es': 'Ilustración', 'en': 'Illustration'},
        [
            (
                {'ca': 'Il·lustració editorial / puntual', 'es': 'Ilustración editorial / puntual', 'en': 'Editorial / one-off illustration'},
                {
                    'ca': 'Peça individual per a article, portada, producte o embalatge (fins a 2 rondes de revisió).',
                    'es': 'Pieza individual para artículo, portada, producto o packaging (hasta 2 rondas de revisión).',
                    'en': 'A single piece for an article, cover, product or packaging (up to 2 rounds of revisions).',
                },
            ),
            (
                {'ca': 'Sèrie o col·lecció il·lustrada', 'es': 'Serie o colección ilustrada', 'en': 'Illustrated series or collection'},
                {
                    'ca': 'Conjunt de 3 a 5 peces sota una mateixa línia visual i narrativa per a marca o campanya.',
                    'es': 'Conjunto de 3 a 5 piezas con una misma línea visual y narrativa para marca o campaña.',
                    'en': 'A set of 3 to 5 pieces sharing one visual and narrative line, for a brand or campaign.',
                },
            ),
        ],
    ),
    (
        {'ca': 'Publicitat i Campanyes', 'es': 'Publicidad y Campañas', 'en': 'Advertising & Campaigns'},
        [
            (
                {'ca': 'Campanya gràfica integral', 'es': 'Campaña gráfica integral', 'en': 'Full graphic campaign'},
                {
                    'ca': "Concepte visual i direcció d'art (sense il·lustració), disseny de cartelleria base i adaptacions per a xarxes socials i bàners.",
                    'es': 'Concepto visual y dirección de arte (sin ilustración), diseño de cartelería base y adaptaciones para redes sociales y banners.',
                    'en': 'Visual concept and art direction (no illustration), core poster design and adaptations for social media and banners.',
                },
            ),
            (
                {'ca': 'Campanya il·lustrada a mida', 'es': 'Campaña ilustrada a medida', 'en': 'Custom illustrated campaign'},
                {
                    'ca': 'Il·lustració principal exclusiva per a la campanya i disseny gràfic, aplicada a cartelleria, suports exteriors i formats digitals.',
                    'es': 'Ilustración principal exclusiva para la campaña y diseño gráfico, aplicada a cartelería, soportes exteriores y formatos digitales.',
                    'en': 'An exclusive key illustration for the campaign plus graphic design, applied to posters, outdoor media and digital formats.',
                },
            ),
        ],
    ),
    (
        {'ca': 'Editorial', 'es': 'Editorial', 'en': 'Editorial'},
        [
            (
                {'ca': 'Maquetació i disseny editorial', 'es': 'Maquetación y diseño editorial', 'en': 'Layout and editorial design'},
                {
                    'ca': "Disseny de retícula, maquetació interior de text i imatge, coberta gràfica i preparació d'arts finals per a impremta (catàlegs, memòries, guies o dossiers).",
                    'es': 'Diseño de retícula, maquetación interior de texto e imagen, cubierta gráfica y preparación de artes finales para imprenta (catálogos, memorias, guías o dosieres).',
                    'en': 'Grid design, interior layout of text and images, cover design and print-ready artwork (catalogues, reports, guides or press kits).',
                },
            ),
            (
                {'ca': 'Llibre o conte il·lustrat integral', 'es': 'Libro o cuento ilustrado integral', 'en': 'Fully illustrated book or story'},
                {
                    'ca': "Direcció d'art completa: coberta, contracoberta, llom i guardes, il·lustracions interiors a mida, maquetació de textos i preparació d'arts finals per a impremta.",
                    'es': 'Dirección de arte completa: cubierta, contracubierta, lomo y guardas, ilustraciones interiores a medida, maquetación de textos y preparación de artes finales para imprenta.',
                    'en': 'Complete art direction: front and back cover, spine and endpapers, custom interior illustrations, text layout and print-ready artwork.',
                },
            ),
        ],
    ),
    (
        {'ca': 'Disseny Web / Digital', 'es': 'Diseño Web / Digital', 'en': 'Web / Digital Design'},
        [
            (
                {'ca': 'Disseny web UI/UX (No-Code)', 'es': 'Diseño web UI/UX (No-Code)', 'en': 'UI/UX web design (no-code)'},
                {
                    'ca': 'Arquitectura bàsica, disseny visual responsive i maquetació web (landing o lloc corporatiu de 4–5 seccions).',
                    'es': 'Arquitectura básica, diseño visual responsive y maquetación web (landing o web corporativa de 4–5 secciones).',
                    'en': 'Basic site structure, responsive visual design and web build (a landing page or a 4–5 section company site).',
                },
            ),
            (
                {'ca': 'Disseny web + desenvolupament a mida', 'es': 'Diseño web + desarrollo a medida', 'en': 'Web design + custom development'},
                {
                    'ca': 'Disseny UI/UX complet i direcció creativa, amb programació a mida en col·laboració amb un desenvolupador extern (funcionalitats avançades o codi propi).',
                    'es': 'Diseño UI/UX completo y dirección creativa, con programación a medida en colaboración con un desarrollador externo (funcionalidades avanzadas o código propio).',
                    'en': 'Complete UI/UX design and creative direction, with custom code built together with an external developer (advanced features or bespoke code).',
                },
            ),
        ],
    ),
    (
        {'ca': 'Animació', 'es': 'Animación', 'en': 'Animation'},
        [
            (
                {'ca': 'Animació 2D il·lustrada', 'es': 'Animación 2D ilustrada', 'en': 'Illustrated 2D animation'},
                {
                    'ca': 'Peces animades frame by frame (bucles, il·lustracions animades o microanimacions per a xarxes i web), amb il·lustració, muntatge i exportació final.',
                    'es': 'Piezas animadas frame a frame (bucles, ilustraciones animadas o microanimaciones para redes y web), con ilustración, montaje y exportación final.',
                    'en': 'Frame-by-frame animated pieces (loops, animated illustrations or micro-animations for social media and web), including illustration, editing and final export.',
                },
            ),
        ],
    ),
    (
        {'ca': 'Murals', 'es': 'Murales', 'en': 'Murals'},
        [
            (
                {'ca': 'Intervenció puntual / window art', 'es': 'Intervención puntual / window art', 'en': 'One-off piece / window art'},
                {
                    'ca': 'Disseny i pintura artesanal en vidrieres, aparadors o espais de format reduït. Inclou materials bàsics i desplaçament local.',
                    'es': 'Diseño y pintura artesanal en cristaleras, escaparates o espacios de formato reducido. Incluye materiales básicos y desplazamiento local.',
                    'en': 'Hand-painted design on glass, shop windows or small spaces. Basic materials and local travel included.',
                },
            ),
            (
                {'ca': 'Mural a gran escala', 'es': 'Mural a gran escala', 'en': 'Large-scale mural'},
                {
                    'ca': "Esbós conceptual a escala adaptat a l'espai i execució tècnica in situ sobre parets o grans superfícies. Inclou materials bàsics i desplaçament local.",
                    'es': 'Boceto conceptual a escala adaptado al espacio y ejecución técnica in situ sobre paredes o grandes superficies. Incluye materiales básicos y desplazamiento local.',
                    'en': 'A scaled concept sketch fitted to the space and on-site painting on walls or large surfaces. Basic materials and local travel included.',
                },
            ),
        ],
    ),
    (
        {'ca': 'Col·laboracions recurrents', 'es': 'Colaboraciones recurrentes', 'en': 'Ongoing collaborations'},
        [
            (
                {'ca': 'Suport gràfic per hores', 'es': 'Soporte gráfico por horas', 'en': 'Hourly design support'},
                {
                    'ca': "Per a empreses o agències que necessiten suport gràfic àgil: adaptacions de formats, retocs o peces puntuals, amb bosses d'hores mensuals i prioritat de lliurament.",
                    'es': 'Para empresas o agencias que necesitan soporte gráfico ágil: adaptaciones de formatos, retoques o piezas puntuales, con bolsas de horas mensuales y prioridad de entrega.',
                    'en': 'For companies or agencies that need quick design support: format adaptations, touch-ups or one-off pieces, with monthly hour packs and priority delivery.',
                },
            ),
        ],
    ),
]


def seed(apps, schema_editor):
    ServiceGroup = apps.get_model('pages', 'ServiceGroup')
    Service = apps.get_model('pages', 'Service')
    if ServiceGroup.objects.exists():
        return
    for group_order, (group_name, services) in enumerate(INITIAL):
        group = ServiceGroup.objects.create(name_i18n=group_name, order=group_order)
        for order, (name, description) in enumerate(services):
            Service.objects.create(group=group, name_i18n=name, description_i18n=description, order=order)


def unseed(apps, schema_editor):
    apps.get_model('pages', 'ServiceGroup').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0004_services'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
