import base64
import os
import tempfile
import unittest
import base64

from pdf_generator import create_pdf


class TestPDFGenerator(unittest.TestCase):
    """
    Unit tests for PDF report generation.
    Verifies that reports are created successfully under
    different input conditions.
    """

    def tearDown(self):
        """Cleanup generated PDFs after each test."""
        if hasattr(self, "generated_pdf"):
            if os.path.exists(self.generated_pdf):
                os.remove(self.generated_pdf)

    def test_pdf_file_is_created(self):
        """Verify that a PDF report is generated successfully."""
        self.generated_pdf = create_pdf(
            total=100,
            positive=80,
            negative=20,
            chart_path="missing_chart.png"
        )

        self.assertTrue(os.path.exists(self.generated_pdf))

    def test_generated_file_is_pdf(self):
        """Verify that the generated report has a .pdf extension."""
        self.generated_pdf = create_pdf(
            total=50,
            positive=30,
            negative=20,
            chart_path="missing_chart.png"
        )

        self.assertTrue(self.generated_pdf.endswith(".pdf"))

    def test_report_generation_without_chart(self):
        """
        Verify report generation works even when
        the chart image is not available.
        """
        
        self.generated_pdf = create_pdf(
            total=25,
            positive=15,
            negative=10,
            chart_path="does_not_exist.png"
        )

        self.assertTrue(os.path.exists(self.generated_pdf))

    def test_summary_and_recommendations_generation(self):
        """
        Verify summary and recommendation sections
        do not raise exceptions during PDF creation.
        """
        self.generated_pdf = create_pdf(
            total=200,
            positive=150,
            negative=50,
            chart_path="missing_chart.png"
        )

        self.assertTrue(os.path.exists(self.generated_pdf))

    def test_report_generation_with_chart(self):
        """
        Verify report generation works when a valid
        chart image is supplied.
        """

        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z5XQAAAAASUVORK5CYII="
        )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".png"
        ) as tmp_chart:
            tmp_chart.write(png_data)
            chart_path = tmp_chart.name

        try:
            self.generated_pdf = create_pdf(
                total=100,
                positive=70,
                negative=30,
                chart_path=chart_path
            )

            self.assertTrue(os.path.exists(self.generated_pdf))

        finally:
            if os.path.exists(chart_path):
                os.remove(chart_path)

if __name__ == "__main__":
    unittest.main()