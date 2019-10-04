from django.db import migrations


# noinspection PyPep8Naming,PyUnusedLocal
def create_decision_types(apps, schema_editor):
    ProcType = apps.get_model('conferences', 'ProceedingType')
    ReviewDecisionType = apps.get_model('review', 'ReviewDecisionType')

    rsci = ProcType.objects.filter(name__icontains='rsci').first()
    springer = ProcType.objects.filter(name__icontains='springer').first()
    assert rsci is not None
    assert springer is not None

    reject = ReviewDecisionType.objects.create(
        decision='REJECT', description='Rejected after review')
    accept_rsci = ReviewDecisionType.objects.create(
        decision='ACCEPT', description='Accept to RSCI volume')
    accept_rsci.allowed_proceedings.add(rsci)
    accept_springer = ReviewDecisionType.objects.create(
        decision='ACCEPT', description='Accept to Springer volume')
    accept_springer.allowed_proceedings.add(rsci)
    accept_springer.allowed_proceedings.add(springer)


# noinspection PyPep8Naming,PyUnusedLocal
def create_new_style_decisions(apps, schema_editor):
    ProcType = apps.get_model('conferences', 'ProceedingType')
    DecisionType = apps.get_model('review', 'ReviewDecisionType')
    OldDecision = apps.get_model('review', 'DecisionOLD')
    NewDecision = apps.get_model('review', 'ReviewDecision')
    VolumeAssignment = apps.get_model('proceedings', 'VolumeAssignment')

    rsci = ProcType.objects.filter(name__icontains='rsci').first()
    springer = ProcType.objects.filter(name__icontains='springer').first()

    reject = DecisionType.objects.filter(decision='REJECT').first()
    accept_rsci = DecisionType.objects.filter(
        decision='ACCEPT', description__icontains='rsci').first()
    accept_springer = DecisionType.objects.filter(
        decision='ACCEPT', description__icontains='springer').first()

    created_decisions = []
    created_assignments = []
    for decision in OldDecision.objects.all():
        submission = decision.submission
        stage = submission.reviewstage_set.first()
        if stage is None or (hasattr(stage, 'decision') and stage.decision):
            print(f'\n[!!!] skipping decision for submission #{submission.id}'
                  f': no decision or stage found')
            continue
        decision_type = None
        if decision.decision == 'REJECT':
            decision_type = reject
        elif decision.decision == 'ACCEPT':
            if decision.proc_type == rsci:
                decision_type = accept_rsci
            elif decision.proc_type == springer:
                decision_type = accept_springer
        created_decisions.append(
            NewDecision(decision_type=decision_type, stage=stage))
        if decision_type is accept_rsci:
            created_assignments.append(VolumeAssignment(
                submission=submission, proc_type=rsci, volume=decision.volume,
                active=True))
        if decision_type is accept_springer:
            created_assignments.append(VolumeAssignment(
                submission=submission, proc_type=springer,
                volume=decision.volume, active=True))
            # Since that was Springer-accepted submission, volume assignment
            # is for Springer proceedings. For RSCI, set volume to None:
            created_assignments.append(VolumeAssignment(
                submission=submission, proc_type=rsci, volume=None,
                active=True))
    NewDecision.objects.bulk_create(created_decisions)
    VolumeAssignment.objects.bulk_create(created_assignments)


class Migration(migrations.Migration):

    dependencies = [
        ('review', '0010_reviewdecision'),
        ('proceedings', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_decision_types),
        migrations.RunPython(create_new_style_decisions),
    ]
