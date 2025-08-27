class CustomAccountManager(BaseUserManager):
    def create_superuser(self, email, username=None, first_name=None, last_name=None, password=None, **other_fields):
        other_fields.setdefault('is_superuser', True)
        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_active', True)
        other_fields.setdefault('is_verified', True)

        if other_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must be assigned to is_superuser=True'))

        if other_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must be assigned to is_staff=True'))

        if not username:
            username = email.split('@')[0]

        # Pass role through extra_fields instead of as a separate argument
        return self.create_user(email, username, first_name, last_name, password, **other_fields)

    def create_user(self, email, first_name="", last_name="", role="student", password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)

        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            **extra_fields
        )

        if not user.username:
            base_username = "new_user"
            counter = 1
            username = f"{base_username}_{counter}"
            while CustomUser.objects.filter(username=username).exists():
                counter += 1
                username = f"{base_username}_{counter}"
            user.username = username

        user.set_password(password)
        user.save(using=self._db)
        return user