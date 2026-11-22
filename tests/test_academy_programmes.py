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
            self.assertContains(response, "Copy link")
            self.assertNotContains(response, "Post to LinkedIn")
            self.assertContains(response, "Target Roles")
            self.assertContains(response, "Market Pay Benchmark")
            self.assertContains(response, 'property="og:title"')
            self.assertContains(response, 'property="og:description"')

    def test_generate_programme_linkedin_post(self):
        from apps.training.linkedin import generate_programme_linkedin_post
        from apps.training.models import Programme

        prog = Programme.objects.filter(slug="agile-training").first()
        self.assertIsNotNone(prog)
        post_text = generate_programme_linkedin_post(prog)
        self.assertIn("Scrum Master", post_text)
        self.assertIn("NO CODING REQUIRED", post_text)
        self.assertIn("$115,875", post_text)
        self.assertIn("https://gctekton.com/training/agile-training/", post_text)
        self.assertIn("#GCTT", post_text)

    def test_generate_job_linkedin_post(self):
        from apps.jobs.linkedin import generate_linkedin_post_text
        from apps.jobs.models import Job

        job = Job.objects.first()
        if job:
            post_text = generate_linkedin_post_text(job)
            self.assertIn("OPT / STEM OPT", post_text)
            self.assertIn("H-4 EAD", post_text)
            self.assertIn("Green Card (GC)", post_text)
            self.assertIn("U.S. Citizens", post_text)
            self.assertIn("#W2Jobs", post_text)

    def test_home_page_contact_markup(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<dl class="mt-8 space-y-4 text-sm">')
        self.assertContains(response, "Start a conversation.")
        self.assertContains(response, "Headquarters")

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
        result_agile = analyze_career_trajectory("", "", "Agile Training")
        self.assertEqual(result_agile["programme"], "Agile Training")
        self.assertNotEqual(result_agile["programme"], "AI BA")
        result_ai = analyze_career_trajectory("", "", "AI")
        self.assertEqual(result_ai["programme"], "AI BA")

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
