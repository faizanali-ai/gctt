from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.accounts.apps import assign_permissions
from apps.accounts.models import TeamProfile, User
from apps.enquiries.models import Enquiry
from apps.jobs.models import Application, Job
from apps.training.models import Category, Programme


class AdminDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        assign_permissions()
        cls.admin = User.objects.create_superuser(
            email="console-admin@example.com", password="test-pass-12345"
        )
        cls.staff = User.objects.create_user(
            email="console-staff@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=True,
        )
        cls.staff.groups.add(Group.objects.get(name="Recruiter"))
        cls.candidate = User.objects.create_user(
            email="console-candidate@example.com", password="test-pass-12345"
        )
        cls.student = User.objects.create_user(
            email="console-student@example.com",
            password="test-pass-12345",
            account_type=User.AccountType.STUDENT,
        )

    def test_user_directory_lists_every_designation(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("manage_users"))
        self.assertContains(response, self.admin.email)
        self.assertContains(response, self.staff.email)
        self.assertContains(response, self.candidate.email)
        self.assertContains(response, self.student.email)
        self.assertContains(response, "Training Student")

    def test_candidate_can_be_promoted_to_staff(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("manage_user_edit", args=[self.candidate.pk]),
            {
                "email": self.candidate.email,
                "first_name": "Console",
                "last_name": "Candidate",
                "phone": "",
                "designation": "staff",
                "group": "Recruiter",
                "is_active": "on",
                "email_verified": "on",
                "password": "",
            },
        )
        self.assertRedirects(response, reverse("manage_users"))
        self.candidate.refresh_from_db()
        self.assertTrue(self.candidate.is_staff)
        self.assertEqual(self.candidate.designation, "Staff")
        self.assertEqual(
            list(self.candidate.groups.values_list("name", flat=True)), ["Recruiter"]
        )

    def test_staff_can_be_changed_to_student(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("manage_user_edit", args=[self.staff.pk]),
            {
                "email": self.staff.email,
                "first_name": "Console",
                "last_name": "Staff",
                "phone": "",
                "designation": "student",
                "is_active": "on",
                "email_verified": "on",
                "password": "",
            },
        )
        self.assertRedirects(response, reverse("manage_users"))
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_staff)
        self.assertEqual(self.staff.designation, "Training Student")
        self.assertEqual(self.staff.groups.count(), 0)

    def test_provisioned_candidate_can_log_in(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("manage_user_create"),
            {
                "email": "new-candidate@example.com",
                "first_name": "New",
                "last_name": "Candidate",
                "phone": "",
                "designation": "candidate",
                "password": "test-pass-12345",
                "is_active": "on",
                "email_verified": "on",
            },
        )
        self.assertRedirects(response, reverse("manage_users"))
        user = User.objects.get(email="new-candidate@example.com")
        self.assertFalse(user.is_staff)
        self.assertEqual(user.designation, "Candidate")
        self.assertTrue(user.email_verified)
        self.client.logout()
        login = self.client.post(
            reverse("login"),
            {"username": "new-candidate@example.com", "password": "test-pass-12345"},
        )
        self.assertRedirects(login, reverse("dashboard"))

    def test_portal_labels_candidate_dashboard(self):
        self.client.force_login(self.candidate)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Candidate")
        self.assertNotContains(response, "Django admin")

    def test_admin_site_is_not_available(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 404)

    def test_team_designation_is_editable(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("manage_team_create"),
            {
                "section": TeamProfile.Section.TEAM,
                "name": "Console Person",
                "designation": "Senior Consultant",
                "bio": "",
                "linkedin_url": "",
                "photo_url": "",
                "order": 1,
                "published": "on",
            },
        )
        self.assertRedirects(response, reverse("manage_team"))
        profile = TeamProfile.objects.get(name="Console Person")
        self.assertEqual(profile.designation, "Senior Consultant")
        response = self.client.post(
            reverse("manage_team_edit", args=[profile.pk]),
            {
                "section": TeamProfile.Section.TEAM,
                "name": "Console Person",
                "designation": "Principal Consultant",
                "bio": "",
                "linkedin_url": "",
                "photo_url": "",
                "order": 1,
                "published": "on",
            },
        )
        self.assertRedirects(response, reverse("manage_team"))
        profile.refresh_from_db()
        self.assertEqual(profile.designation, "Principal Consultant")
        self.assertContains(self.client.get(reverse("about")), "Principal Consultant")

    def test_job_crud_reflects_on_public_careers(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("staff_job_create"),
            {
                "title": "Console Engineer",
                "slug": "",
                "location": "Irving, TX",
                "employment_type": Job.EmploymentType.FULL_TIME,
                "description": "Build things.",
                "requirements": "",
                "published": "on",
            },
        )
        self.assertRedirects(response, reverse("staff_jobs"))
        job = Job.objects.get(title="Console Engineer")
        self.assertContains(self.client.get(reverse("careers")), "Console Engineer")
        response = self.client.post(
            reverse("staff_job_edit", args=[job.pk]),
            {
                "title": "Console Engineer II",
                "slug": job.slug,
                "location": "Irving, TX",
                "employment_type": Job.EmploymentType.FULL_TIME,
                "description": "Build things.",
                "requirements": "",
            },
        )
        self.assertRedirects(response, reverse("staff_jobs"))
        job.refresh_from_db()
        self.assertEqual(job.title, "Console Engineer II")
        self.assertFalse(job.published)
        response = self.client.post(reverse("staff_job_delete", args=[job.pk]))
        self.assertRedirects(response, reverse("staff_jobs"))
        self.assertFalse(Job.objects.filter(pk=job.pk).exists())

    def test_category_and_programme_crud(self):
        self.client.force_login(self.admin)
        category = Category.objects.create(name="Console Track", published=True)
        response = self.client.post(
            reverse("staff_programme_create"),
            {
                "title": "Console Programme",
                "slug": "",
                "category": category.pk,
                "delivery_mode": Programme.DeliveryMode.ONLINE,
                "schedule": "",
                "duration": "",
                "description": "Learn things.",
                "registration_open": "on",
                "published": "on",
                "order": 1,
            },
        )
        self.assertRedirects(response, reverse("staff_programmes"))
        programme = Programme.objects.get(title="Console Programme")
        self.assertContains(self.client.get(reverse("training")), "Console Programme")
        response = self.client.post(
            reverse("staff_category_edit", args=[category.pk]),
            {"name": "Console Track II", "published": "on", "order": 2},
        )
        self.assertRedirects(response, reverse("staff_categories"))
        category.refresh_from_db()
        self.assertEqual(category.name, "Console Track II")
        response = self.client.post(reverse("staff_programme_delete", args=[programme.pk]))
        self.assertRedirects(response, reverse("staff_programmes"))

    def test_application_and_enquiry_records_are_manageable(self):
        job = Job.objects.create(title="Console Role", location="Irving", description="x")
        application = Application.objects.create(
            job=job,
            applicant=self.candidate,
            resume=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 console", content_type="application/pdf"),
        )
        enquiry = Enquiry.objects.create(name="Console Enquiry", email="e@example.com", message="Hi")
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("staff_application_edit", args=[application.uuid]),
            {"status": Application.Status.SHORTLISTED, "message": "Looks good."},
        )
        self.assertRedirects(response, reverse("staff_applications"))
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.SHORTLISTED)
        response = self.client.post(
            reverse("staff_enquiry_edit", args=[enquiry.pk]),
            {
                "name": "Console Enquiry II",
                "email": "e@example.com",
                "phone": "",
                "company": "",
                "area": "",
                "how_heard": "",
                "category": Enquiry.Category.GENERAL,
                "message": "Hi",
                "status": Enquiry.Status.RESOLVED,
            },
        )
        self.assertRedirects(response, reverse("staff_enquiries"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.RESOLVED)
        self.assertEqual(enquiry.name, "Console Enquiry II")

    def test_audit_log_is_read_only(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("staff_category_create"),
            {"name": "Audit Track", "published": "on", "order": 1},
        )
        response = self.client.get(reverse("manage_audit"))
        self.assertContains(response, "category.create")
        self.assertNotContains(response, "Delete selected")

    def test_repair_command_fixes_broken_internal_flags_only(self):
        broken = User.objects.create_user(
            email="broken-staff@example.com",
            password="test-pass-12345",
            role=User.Role.STAFF,
            is_staff=False,
        )
        broken.groups.add(Group.objects.get(name="Trainer"))
        untouched = User.objects.create_user(
            email="untouched-candidate@example.com", password="test-pass-12345"
        )
        call_command("repair_internal_accounts", "--apply")
        broken.refresh_from_db()
        untouched.refresh_from_db()
        self.assertTrue(broken.is_staff)
        self.assertFalse(broken.is_superuser)
        self.assertFalse(untouched.is_staff)

    def test_non_admin_staff_cannot_use_manage_pages(self):
        self.client.force_login(self.staff)
        for name in ("manage_users", "manage_team", "manage_audit"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
