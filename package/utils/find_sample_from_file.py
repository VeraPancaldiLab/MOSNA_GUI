def find_sample_from_file(file, column_patient, column_sample):
    if column_sample is None:
        return file.stem.split(column_patient)[1][1:], None
    else:
        file = file.stem.split(column_sample)
        sample = file[1][1:]
        patient = file[0].split(column_patient)[1][1:-1]
        return patient, sample