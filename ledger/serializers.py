from rest_framework import serializers
from .models import Account, JournalEntry, JournalLine


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'


class JournalLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalLine
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):

    lines = JournalLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = '__all__'

    def create(self, validated_data):

        lines_data = validated_data.pop('lines')

        entry = JournalEntry.objects.create(**validated_data)

        for line in lines_data:
            JournalLine.objects.create(
                journal_entry=entry,
                **line
            )

        return entry