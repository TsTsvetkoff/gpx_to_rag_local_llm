import os
import gpxpy

# Define your input and output directories
input_dir = 'my_gpx_to_xml'
output_dir = 'parsed_xmls'

# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Iterate through all files in the input directory
for filename in os.listdir(input_dir):
    if filename.endswith('.gpx'):
        input_filepath = os.path.join(input_dir, filename)
        print(f"Processing: {input_filepath}")

        # Open and parse the GPX file
        with open(input_filepath, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            gpx_xml = gpx.to_xml()

        # Prepare the output file path; change extension to .xml
        output_filename = os.path.splitext(filename)[0] + '.xml'
        output_filepath = os.path.join(output_dir, output_filename)

        # Write the XML data to the output file
        with open(output_filepath, 'w') as xml_file:
            xml_file.write(gpx_xml)

        print(f"Converted '{filename}' to '{output_filename}' in directory '{output_dir}'.")
