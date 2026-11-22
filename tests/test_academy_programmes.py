from django.test import Client, TestCase
from django.urls import reverse

from apps.training.ai_advisor import analyze_career_trajectory
from apps.training.views import visible_programmes


class AcademyProgrammesTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_visible_programmes_contains_five_tracks(self):
        programmes = visible_programmes()
        titles = list(programmes.values_list("title", flat=True))
        for expected in ["Agile Training", "Business Analyst", "DevOps", "BA SM", "AI BA"]:
            self.assertIn(expected, titles)

    def test_academy_page_renders_programmes(self):
        response = self.client.get(reverse("training"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No cohorts are open right now.")

        for expected in ["Agile Training", "Business Analyst", "DevOps", "BA SM", "AI BA"]:
            self.assertContains(response, expected)

        for expected_category in [
            "Agile &amp; Scrum",
            "Business Analysis",
            "Cloud &amp; DevOps",
            "Hybrid Delivery",
            "AI &amp; Emerging Tech",
        ]:
            self.assertContains(response, expected_category)

    def test_programme_detail_pages_accessible(self):
        for slug in ["agile-training", "business-analyst", "devops", "ba-sm", "ai-ba"]:
            url = reverse("programme_detail", kwargs={"slug": slug})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Detail page failed for {slug}")
            self.assertContains(response, "Join this cohort")
            self.assertContains(response, "Share this programme")

    def test_ai_career_advisor_archetypes(self):
        # AI BA match
        result = analyze_career_trajectory("Data Specialist", "3-5", "ai ba and llm prompt engineering")
        self.assertEqual(result["programme"], "AI BA")

        # BA SM match
        result = analyze_career_trajectory("Scrum Lead", "3-5", "ba sm dual hybrid delivery")
        self.assertEqual(result["programme"], "BA SM")

        # Business Analyst match
        result = analyze_career_trajectory("Analyst", "3-5", "business analyst requirements gathering")
        self.assertEqual(result["programme"], "Business Analyst")

        # Agile Training match
        result = analyze_career_trajectory("Project Lead", "3-5", "scrum master and agile leadership")
        self.assertEqual(result["programme"], "Agile Training")

        # DevOps match
        result = analyze_career_trajectory("Linux Admin", "3-5", "cloud engineering and devops docker")
        self.assertEqual(result["programme"], "DevOps")

    def test_ai_keyword_matches_only_as_a_standalone_term(self):
        self.assertEqual(analyze_career_trajectory("Agile Training")["programme"], "Agile Training")
        self.assertEqual(analyze_career_trajectory(interests="(AI)")["programme"], "AI BA")

    def test_api_career_advisor_endpoint(self):
        url = reverse("api_career_advisor")
        response = self.client.post(
            url,
            data={"role": "Business Analyst", "experience": "3-5", "interests": "requirements"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data.get("success"))
        self.assertIn("data", json_data)
        self.assertEqual(json_data["data"]["programme"], "Business Analyst")
