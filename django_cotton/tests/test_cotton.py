from django.test import TestCase

from django_cotton.tests.inline_test_case import CottonInlineTestCase
from django_cotton.tests.utils import get_compiled, get_rendered


class InlineTestCase(CottonInlineTestCase):
    def test_component_is_rendered(self):
        self.create_template(
            "cotton/component.html",
            """<div class="i-am-component">{{ slot }}</div>""",
        )

        self.create_template(
            "view.html",
            """<c-component>Hello, World!</c-component>""",
        )

        # Register Url
        self.register_url("view/", self.make_view("view.html"))

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.get_url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, '<div class="i-am-component">')
            self.assertContains(response, "Hello, World!")

    def test_new_lines_in_attributes_are_preserved(self):
        self.create_template(
            "cotton/component.html",
            """<div {{ attrs }}>{{ slot }}</div>""",
        )

        self.create_template(
            "view.html",
            """
            <c-component x-data="{
                attr1: 'im an attr',
                var1: 'im a var',
                method() {
                    return 'im a method';
                }
            }" />
            """,
        )

        # Register Url
        self.register_url("view/", self.make_view("view.html"))

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.get_url_conf()):
            response = self.client.get("/view/")

            self.assertTrue(
                """{
                attr1: 'im an attr',
                var1: 'im a var',
                method() {
                    return 'im a method';
                }
            }"""
                in response.content.decode()
            )

    def test_attribute_names_on_component_containing_hyphens_are_converted_to_underscores(
        self,
    ):
        self.create_template(
            "cotton/component.html",
            """
            <div x-data="{{ x_data }}" x-init="{{ x_init }}"></div>
            """,
        )

        self.create_template(
            "view.html",
            """
            <c-component x-data="{}" x-init="do_something()" />
            """,
        )

        # Register Url
        self.register_url("view/", self.make_view("view.html"))

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.get_url_conf()):
            response = self.client.get("/view/")

            self.assertContains(response, 'x-data="{}" x-init="do_something()"')

    def test_attribute_names_on_cvars_containing_hyphens_are_converted_to_underscores(
        self,
    ):
        self.create_template(
            "cotton/component.html",
            """
            <c-vars x-data="{}" x-init="do_something()" />
            
            <div x-data="{{ x_data }}" x-init="{{ x_init }}"></div>
            """,
        )

        self.create_template(
            "view.html",
            """
            <c-component />
            """,
        )

        # Register Url
        self.register_url("view/", self.make_view("view.html"))

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.get_url_conf()):
            response = self.client.get("/view/")

            self.assertContains(response, 'x-data="{}" x-init="do_something()"')


class CottonTestCase(TestCase):
    def test_parent_component_is_rendered(self):
        response = self.client.get("/parent")
        self.assertContains(response, '<div class="i-am-parent">')

    def test_child_is_rendered(self):
        response = self.client.get("/child")
        self.assertContains(response, '<div class="i-am-parent">')
        self.assertContains(response, '<div class="i-am-child">')

    def test_self_closing_is_rendered(self):
        response = self.client.get("/self-closing")
        self.assertContains(response, '<div class="i-am-parent">')

    def test_named_slots_correctly_display_in_loop(self):
        response = self.client.get("/named-slot-in-loop")
        self.assertContains(response, "item name: Item 1")
        self.assertContains(response, "item name: Item 2")
        self.assertContains(response, "item name: Item 3")

    def test_attribute_passing(self):
        response = self.client.get("/attribute-passing")
        self.assertContains(
            response, '<div attribute_1="hello" and-another="woo1" thirdforluck="yes">'
        )

    def test_attribute_merging(self):
        response = self.client.get("/attribute-merging")
        self.assertContains(
            response, 'class="form-group another-class-with:colon extra-class"'
        )

    def test_django_syntax_decoding(self):
        response = self.client.get("/django-syntax-decoding")
        self.assertContains(response, "some-class")

    def test_vars_are_converted_to_vars_frame_tags(self):
        compiled = get_compiled(
            """
            <c-vars var1="string with space" />
            
            content
        """
        )

        self.assertEquals(
            compiled,
            """{% cotton_vars_frame var1=var1|default:"string with space" %}content{% endcotton_vars_frame %}""",
        )

    def test_attrs_do_not_contain_vars(self):
        response = self.client.get("/vars-test")
        self.assertContains(response, "attr1: 'im an attr'")
        self.assertContains(response, "var1: 'im a var'")
        self.assertContains(response, """attrs: 'attr1="im an attr"'""")

    def test_strings_with_spaces_can_be_passed(self):
        response = self.client.get("/string-with-spaces")
        self.assertContains(response, "attr1: 'I have spaces'")
        self.assertContains(response, "var1: 'string with space'")
        self.assertContains(response, "default_var: 'default var'")
        self.assertContains(response, "named_slot: '")
        self.assertContains(response, "named_slot with spaces")
        self.assertContains(response, """attrs: 'attr1="I have spaces"'""")

    def test_named_slots_dont_bleed_into_sibling_components(self):
        html = """
            <c-test-component>
                component1 
                <c-slot name="named_slot">named slot 1</c-slot>
            </c-test-component>
            <c-test-component>
                component2 
            </c-test-component>
        """

        rendered = get_rendered(html)

        self.assertTrue("named_slot: 'named slot 1'" in rendered)
        self.assertTrue("named_slot: ''" in rendered)

    def test_template_variables_are_not_parsed(self):
        html = """
            <c-test-component attr1="variable" :attr2="variable">
                <c-slot name="named_slot">
                    <a href="#" silica:click.prevent="variable = 'lineage'">test</a>
                </c-slot>
            </c-test-component>
        """

        rendered = get_rendered(html, {"variable": 1})

        self.assertTrue("attr1: 'variable'" in rendered)
        self.assertTrue("attr2: '1'" in rendered)

    def test_valueless_attributes_are_process_as_true(self):
        response = self.client.get("/test/valueless-attributes")

        self.assertContains(response, "It's True")

    def test_component_attributes_can_converted_to_python_types(self):
        response = self.client.get("/test/eval-attributes")

        self.assertContains(response, "none is None")
        self.assertContains(response, "number is 1")
        self.assertContains(response, "boolean_true is True")
        self.assertContains(response, "boolean_false is False")
        self.assertContains(response, "list.0 is 1")
        self.assertContains(response, "dict.key is 'value'")
        self.assertContains(response, "listdict.0.key is 'value'")

    def test_cvars_can_be_converted_to_python_types(self):
        response = self.client.get("/test/eval-vars")

        self.assertContains(response, "none is None")
        self.assertContains(response, "number is 1")
        self.assertContains(response, "boolean_true is True")
        self.assertContains(response, "boolean_false is False")
        self.assertContains(response, "list.0 is 1")
        self.assertContains(response, "dict.key is 'value'")
        self.assertContains(response, "listdict.0.key is 'value'")

    def test_attributes_can_contain_django_native_tags(self):
        response = self.client.get("/test/native-tags-in-attributes")

        self.assertContains(response, "Attribute 1 says: 'Hello Will'")
        self.assertContains(response, "Attribute 2 says: 'world'")
        self.assertContains(response, "Attribute 3 says: 'cowabonga!'")

        self.assertContains(
            response,
            """attrs tag is: 'normal="normal" attr1="Hello Will" attr2="world" attr3="cowabonga!"'""",
        )

    # TODO: implement inline test asset creation, i.e. store_template("native-tags-in-attributes", """)
