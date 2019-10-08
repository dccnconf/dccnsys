from django.db import migrations


# noinspection PyPep8Naming,PyUnusedLocal
def copy_materials(apps, schema_editor):
    ArtifactDescriptor = apps.get_model('conferences', 'ArtifactDescriptor')
    ExternalFile = apps.get_model('conferences', 'ExternalFile')
    ArtifactDescriptorLink = apps.get_model(
        'conferences', 'ArtifactDescriptorLink')

    updated_descriptors = []
    for ad in ArtifactDescriptor.objects.all():
        if ExternalFile.objects.filter(
                artifactdescriptorlink__descriptor=ad,
                url=ad.materials_url).count() > 0 or ad.materials_url == '':
            continue

        # 1) Create external file
        ef = ExternalFile.objects.create(
            url=ad.materials_url, label='External materials')

        # 2) Bind external file to the artifact:
        link = ArtifactDescriptorLink.objects.create(link=ef, descriptor=ad)

        # 3) Clear the stored link so we can safely remove it:
        ad.materials_url = ''
        updated_descriptors.append(ad)
        print(f'> created ExternalFile {ef.id} for descriptor {ad.id} bound '
              f'through link {link.id}')

    ArtifactDescriptor.objects.bulk_update(
        updated_descriptors, ['materials_url'])


class Migration(migrations.Migration):
    dependencies = [
        ('conferences', '0016_artifactdescriptorlinks_externalfile'),
    ]

    operations = [
        migrations.RunPython(copy_materials),
    ]
