from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from .models import GoalSheet, Goal, QuarterlyAchievement


class GoalSheetForm(forms.ModelForm):
    class Meta:
        model = GoalSheet
        fields = ['cycle']
        widgets = {
            'cycle': forms.HiddenInput(),
        }


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['thrust_area', 'title', 'description', 'uom', 'target', 'target_date', 'weightage', 'order', 'is_shared']
        widgets = {
            'description': forms.Textarea(attrs={'rows':2}),
            'target_date': forms.DateInput(attrs={'type':'date'}),
        }

    def clean_weightage(self):
        w = self.cleaned_data.get('weightage')
        if w is None:
            return w
        if w < Decimal('10'):
            raise forms.ValidationError('Minimum weightage per goal is 10%.')
        return w


from django.forms import inlineformset_factory, BaseInlineFormSet

class BaseGoalFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        
        total_weight = Decimal('0')
        active_goals = 0
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            weight = form.cleaned_data.get('weightage')
            if weight:
                total_weight += weight
                active_goals += 1
                
        if active_goals > 8:
            raise forms.ValidationError("You can have a maximum of 8 goals.")
            
        if total_weight > Decimal('100'):
            raise forms.ValidationError(f"Total weightage cannot exceed 100%. Currently at {total_weight}%.")

GoalFormSet = inlineformset_factory(
    GoalSheet, Goal, form=GoalForm, formset=BaseGoalFormSet,
    extra=1, can_delete=True, min_num=1, validate_min=False
)


class QuarterlyAchievementForm(forms.ModelForm):
    class Meta:
        model = QuarterlyAchievement
        fields = ['actual', 'actual_date', 'status', 'notes']
        widgets = {
            'actual_date': forms.DateInput(attrs={'type':'date'}),
            'notes': forms.Textarea(attrs={'rows':3}),
        }
