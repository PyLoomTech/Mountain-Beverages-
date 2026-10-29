from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        labels = {"rating": "Your rating", "comment": "Your review"}
        widgets = {
            "rating": forms.Select(attrs={"class": "form-select"}),
            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Tell us about the products and service...",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show stars in the dropdown, best rating first
        self.fields["rating"].choices = [(i, f"{i} - {'★' * i}") for i in range(5, 0, -1)]

    def clean_comment(self):
        comment = self.cleaned_data["comment"].strip()
        if len(comment) < 10:
            raise forms.ValidationError("Please write at least 10 characters.")
        return comment