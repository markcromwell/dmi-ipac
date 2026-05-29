"""
End-to-end UAT using Playwright.
Fills the form, submits, verifies results, downloads and parses the PDF.

Install: pip install playwright pypdf2
         python -m playwright install chromium

Run: pytest tests/test_e2e.py --base-url=https://your-app.vercel.app -v
     BASE_URL=https://dmi-ipac.vercel.app pytest tests/test_e2e.py -v
"""
import os, re, json, tempfile, pytest

BASE_URL = os.getenv('BASE_URL', 'http://localhost:3000')


@pytest.fixture(scope='session')
def browser_ctx(playwright):
    browser = playwright.chromium.launch(headless=True)
    ctx = browser.new_context(accept_downloads=True)
    yield ctx
    browser.close()


@pytest.fixture(scope='session')
def page(browser_ctx):
    p = browser_ctx.new_page()
    yield p
    p.close()


class TestDMIApp:
    """Full end-to-end test of the DMI-IPAC web app."""

    def test_page_loads(self, page):
        """App loads and shows DMI branding."""
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
        assert 'DIVERSIFIED MANUFACTURING' in page.inner_text('body')

    def test_default_values_are_reference_case(self, page):
        """Default inputs should match W0230 reference case."""
        page.goto(BASE_URL)
        assert page.input_value('#model') == 'W0230'
        assert page.input_value('#tube_pressure_psig') == '150'
        assert page.input_value('#tube_temp_in_F') == '250'
        assert page.input_value('#tube_flow') == '1423'
        assert page.input_value('#shell_temp_in_F') == '70'
        assert page.input_value('#shell_flow') == '60'

    def test_calculate_reference_case(self, page):
        """Submit reference case and verify key outputs within 5%."""
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')

        # Submit the form (default values = reference case)
        page.click('#calcBtn')

        # Wait for results
        page.wait_for_selector('#resultsSection:not(.hidden)', timeout=15000)

        # Check Q total
        q_text = page.inner_text('#r_q_total')
        q_match = re.search(r'[\d,]+', q_text.replace(',', ''))
        assert q_match, f'Could not parse Q from: {q_text!r}'
        q = float(q_match.group().replace(',', ''))
        assert 270000 < q < 315000, f'Q={q} outside expected range 270k-315k Btu/h'

        # Check tube outlet temp
        t_text = page.inner_text('#r_tube_out')
        t_match = re.search(r'[\d.]+', t_text)
        assert t_match, f'Could not parse tube_out from: {t_text!r}'
        t_out = float(t_match.group())
        assert 88 < t_out < 100, f'tube_out={t_out} outside expected range 88-100°F'

        # Check shell outlet temp
        s_text = page.inner_text('#r_shell_out')
        s_match = re.search(r'[\d.]+', s_text)
        assert s_match
        s_out = float(s_match.group())
        assert 75 < s_out < 85, f'shell_out={s_out} outside expected range 75-85°F'

        # Check condensate
        cond_text = page.inner_text('#r_condensate')
        cond_match = re.search(r'[\d.]+', cond_text)
        assert cond_match
        cond = float(cond_match.group())
        assert 30 < cond < 55, f'condensate={cond} outside expected range 30-55 lb/h'

    def test_no_javascript_errors(self, page):
        """No uncaught JavaScript errors on load or after calculation."""
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
        page.click('#calcBtn')
        page.wait_for_selector('#resultsSection:not(.hidden)', timeout=15000)
        assert not errors, f'JS errors: {errors}'

    def test_pdf_download(self, page, tmp_path):
        """PDF download works and contains expected content."""
        try:
            import pypdf
        except ImportError:
            pytest.skip('pypdf not installed — run: pip install pypdf')

        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
        page.click('#calcBtn')
        page.wait_for_selector('#resultsSection:not(.hidden)', timeout=15000)

        # Download PDF
        with page.expect_download() as dl_info:
            page.click('#pdfBtn')
        download = dl_info.value
        pdf_path = tmp_path / 'datasheet.pdf'
        download.save_as(str(pdf_path))
        assert pdf_path.exists(), 'PDF file was not saved'

        # Parse and verify content
        reader = pypdf.PdfReader(str(pdf_path))
        assert len(reader.pages) >= 1, 'PDF has no pages'
        text = ' '.join(p.extract_text() for p in reader.pages)

        assert 'DIVERSIFIED MANUFACTURING' in text, 'DMI header missing from PDF'
        assert 'W0230' in text, 'Model number missing from PDF'
        assert 'Btu' in text, 'Units missing from PDF'
        # Check at least one numeric result appears
        assert re.search(r'[0-9]{5,}', text), 'No large numeric values in PDF'

    def test_different_model(self, page):
        """Changing model recalculates with different geometry."""
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')

        # Select a larger model
        page.select_option('#model', 'W1400')
        page.click('#calcBtn')
        page.wait_for_selector('#resultsSection:not(.hidden)', timeout=15000)

        area_text = page.inner_text('#r_area')
        area_match = re.search(r'[\d.]+', area_text)
        assert area_match
        area = float(area_match.group())
        # W1400 should have significantly more area than W0230 (20.8 ft²)
        assert area > 30, f'W1400 area={area} ft² — should be > 30 ft²'

    def test_api_returns_json_not_html(self, page):
        """Regression: API must return JSON, not HTML (caught Netlify Python failure)."""
        # Intercept the API call and check Content-Type
        api_responses = []

        def handle_response(response):
            if '/api/calculate' in response.url or '/.netlify/functions/calculate' in response.url:
                api_responses.append({
                    'status': response.status,
                    'content_type': response.headers.get('content-type', ''),
                    'url': response.url,
                })

        page.on('response', handle_response)
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
        page.click('#calcBtn')
        page.wait_for_selector('#resultsSection:not(.hidden)', timeout=15000)

        assert api_responses, 'No API call was observed — fetch may have failed silently'
        resp = api_responses[-1]
        assert resp['status'] == 200, f'API returned HTTP {resp["status"]} (expected 200)'
        assert 'json' in resp['content_type'].lower(), (
            f'API returned Content-Type: {resp["content_type"]!r} — '
            f'expected application/json. This was the Netlify failure mode.'
        )
