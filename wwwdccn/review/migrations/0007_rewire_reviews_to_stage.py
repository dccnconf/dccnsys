from django.db import migrations
from django.db.models import F

from review.utilities import get_average_score


def average(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def get_score(review):
    scores_raw = [review.technical_merit, review.clarity, review.relevance,
                  review.originality]
    scores = [float(score) for score in scores_raw if score]
    return average(scores)


# noinspection PyPep8Naming
def insert_review_stage(apps, schema_editor):
    Submission = apps.get_model('submissions', 'Submission')
    ReviewStage = apps.get_model('review', 'ReviewStage')
    Review = apps.get_model('review', 'Review')
    submissions = Submission.objects.annotate(
        num_reviews_required=F('stype__num_reviews'))
    stages = []
    for sub in submissions:
        if sub.reviewstage_set.count() > 0 or (
                sub.reviews.count() == 0 and sub.status == 'SUBMIT'):
            continue
        scores = [get_score(review) for review in sub.reviews.all()]
        stages.append(ReviewStage(
            submission=sub, num_reviews_required=sub.num_reviews_required,
            score=average(scores),
            locked=(sub.status not in ['REVIEW', 'SUBMIT'])))
    ReviewStage.objects.bulk_create(stages)

    # After review stages were created, we also update reviews:
    reviews = Review.objects.all()
    for rev in reviews:
        stage = rev.paper.reviewstage_set.first()
        if stage is None:
            print(f'broken paper is #{rev.paper.id}')
        else:
            rev.stage = stage
            rev.locked = stage.locked
    Review.objects.bulk_update(reviews, ['stage', 'locked'])


class Migration(migrations.Migration):
    dependencies = [
        ('review', '0006_auto_20190930_1713'),
    ]

    operations = [
        migrations.RunPython(insert_review_stage),
    ]
