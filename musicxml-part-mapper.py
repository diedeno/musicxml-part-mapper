#!/usr/bin/python3

import tkinter as tk
import xml.etree.ElementTree as ET
import argparse
from tkinter import filedialog, messagebox
import os
import sys
import zipfile
import subprocess
import logging
import tempfile


# USER EDITABLE
EXT_APPLICATION = "MuseScore" # if not defined => hide button to launch application
EXT_APP_PATH =  "~/.local/bin/mscore4portable"
LOGFILE = "part-mapper.log"
WORK_DIRECTORY = ""  # Change this to your desired directory

#-----------------------------------------------------------------
# EXT_APP_PATH - if musescore:
#    On Linux: ~/.local/bin/mscore4portable
#    On Windows: C:/Program Files/MuseScore 4/bin/MuseScore4.exe
#    On macOS: /Applications/MuseScore 4.app/Contents/MacOS/mscore
# But any other application can be used
#---------------------------------------------------------------


## do not change hereunder


"""
MusicXML Part mapper

Copyright (c) 2025 Diego Denolf (graffesmusic) - GPLv3

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

# Application Info
VERSION = "1.0.1"
LAST_MODIFIED = "2025-03-03"
LICENSE = "GPLv3"

external_app = os.path.expanduser(EXT_APP_PATH)

# Fallback to the script's directory if WORK_DIRECTORY is not defined or does not exist
if not WORK_DIRECTORY or not os.path.isdir(WORK_DIRECTORY):
    WORK_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    print(f"Work Directory not found. Falling back to script directory: {WORK_DIRECTORY}")

# Try to use LOGFILE, or use a default value if it's not defined
try:
    logfile = LOGFILE if LOGFILE is not None else "part-assign.log"
except NameError:
    logfile = "part-assign.log"

# Set up logging
script_dir = os.path.dirname(os.path.abspath(__file__))
logfile_path = os.path.join(script_dir, logfile)  # Use the resolved log file name

logging.basicConfig(
    filename=logfile_path,  # Use the absolute path to the log file
    level=logging.DEBUG,  # Log debug and above messages
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class InstrumentMapper:
    def __init__(self, root, file_path=None):
        self.root = root
        self.file_path = file_path
        
          # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
       

        # Construct the path to instruments.xml
        instruments_path = os.path.join(script_dir, 'instruments.xml')

        # Load instruments.xml
        try:
            self.instruments_xml = ET.parse(instruments_path).getroot()
        except FileNotFoundError:
            messagebox.showerror("Error", f"Could not find instruments.xml at {instruments_path}. Please ensure the file exists.")
            logging.error(f"Could not find instruments.xml at {instruments_path}.")
            sys.exit(1)
        except ET.ParseError as e:
            messagebox.showerror("Error", f"Failed to parse instruments.xml: {e}")
            logging.error(f"Failed to parse instruments.xml: {e}")
            sys.exit(1)

        # Rest of the initialization code
        
        #self.instruments_xml = ET.parse('instruments.xml').getroot()
        self.instruments_with_details = []
        self.filtered_instruments = []
        
        # Set up the GUI
        self.setup_gui()
        
        
        # Initialize variables
        self.musicxml_tree = None
        self.musicxml_root = None
        self.parts = []
        self.current_part_index = 0
        
        print("Starting app")
        print(f"Work Directory: {WORK_DIRECTORY}") 
        

    def setup_gui(self):
        """Set up the main application window and widgets."""
        self.root.title("Map Instrument")
        self.root.geometry("750x700")
        
         # Define Tkinter variables
        self.part_name_var = tk.StringVar()
        self.instrument_name_var = tk.StringVar()
        self.transpose_var = tk.StringVar()  # Holds transposition value

        
        #title
        tk.Label(self.root, text="Musicxml Part & Instrument mapper", font=("Helvetica", 14), fg="blue").pack(pady=10, padx=10, anchor="w")

        # File selection - browse and file input on the same line
        frame_file = tk.Frame(self.root)
        frame_file.pack(pady=10, fill="x")
                
        label_file_path = tk.Label(frame_file, text="Select musicxml file:")
        label_file_path.pack(side=tk.LEFT, padx=5)

        self.entry_file_path = tk.Entry(frame_file, width=50)
        self.entry_file_path.pack(side=tk.LEFT, padx=5)

        button_browse = tk.Button(frame_file, text="Browse", command=self.browse_file)
        button_browse.pack(side=tk.LEFT, padx=5)
        
        # Create a frame to hold the button and label
        button_frame = tk.Frame(self.root)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

        # Add the Start button to the frame (aligned to the left)
        self.start_button = tk.Button(
            button_frame, text="Start part mapping", font=("Helvetica", 12, "bold"), command=self.start_mapping
        )
        self.start_button.pack(side=tk.LEFT, padx=10, pady=10)  # Use side=tk.LEFT

        # Add the label to the frame (aligned to the left, next to the button)
        self.label = tk.Label(
            button_frame, text="Mapping instrument for: ", font=("Arial", 12, "bold")
        )
        self.label.pack(side=tk.LEFT, padx=10, pady=10)  # Use side=tk.LEFT

        # Create frames
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        search_label = tk.Label(search_frame, text="Search Instrument:")
        search_label.pack(side=tk.LEFT)
        self.search_box = tk.Entry(search_frame)
        self.search_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        list_frame = tk.Frame(main_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.Y)

        detail_frame = tk.Frame(main_frame)
        detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.instrument_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=30)
        self.instrument_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.instrument_listbox.yview)

        self.detail_text = tk.Text(detail_frame, wrap=tk.WORD, width=50, height=20)
        self.detail_text.pack(fill=tk.BOTH, expand=True)

         # Create the button frame and pack buttons into it
        button_frame = tk.Frame(self.root)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=10)  # Pack the button frame at the top

        # Create the buttons in the button_frame
        select_button = tk.Button(button_frame, text="Select", command=self.save_mappings)
        select_button.pack(side=tk.LEFT, padx=10)

        skip_button = tk.Button(button_frame, text="Skip", command=self.skip_mapping)
        skip_button.pack(side=tk.LEFT, padx=10)

        abort_button = tk.Button(button_frame, text="Exit", command=self.root.destroy)
        abort_button.pack(side=tk.LEFT, padx=10)
        
        button_save = tk.Button(button_frame, text="Save MusicXML", command=self.save_musicxml)
        button_save.pack(side=tk.LEFT, padx=10)
        
        #launch_button = tk.Button(button_frame, text=(f"Launch {APPLICATION}"), command=self.launch_app)
        #launch_button.pack(pady=20)
        # Check if APPLICATION is defined before creating the button
        if 'EXT_APPLICATION' in globals():
            launch_button = tk.Button(
                button_frame, text=f"Launch {EXT_APPLICATION}", command=self.launch_app
            )
            launch_button.pack(pady=20)

        # Create and pack the version label below the button frame
        tk.Label(self.root, text=f"Version: {VERSION}  | Last Modified: {LAST_MODIFIED} | License: {LICENSE}",
                 font=("Helvetica", 10), fg="grey").pack(side=tk.TOP, pady=10, padx=10, anchor="w")

        # Populate the listbox with instruments
        self.populate_listbox()

        # Bind events
        self.instrument_listbox.bind("<<ListboxSelect>>", self.show_instrument_details)
        self.search_box.bind("<KeyRelease>", self.filter_instruments)


    def extract_mxl(self, file_path):
        """
        Extract the contents of an .mxl file and return the path to the main MusicXML file.
        """
        try:
            # Create a temporary directory to extract the .mxl file
            temp_dir = tempfile.mkdtemp()
            
            # Open the .mxl file as a ZIP archive
            with zipfile.ZipFile(file_path, 'r') as mxl_file:
                # Extract all files to the temporary directory
                mxl_file.extractall(temp_dir)
                
                # Look for the main MusicXML file (usually named 'score.xml')
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.xml') or file.endswith('.musicxml'):
                            return os.path.join(root, file)
            
            # If no XML file is found, raise an error
            raise ValueError("No MusicXML file found in the .mxl archive.")
        except Exception as e:
            print(f"Error extracting .mxl file: {e}")
            raise

 
    def browse_file(self):
        """Open a file chooser dialog and update the entry widget with the selected file path."""
        file_path = filedialog.askopenfilename(
            initialdir=WORK_DIRECTORY,  # Start browsing from the work directory
            filetypes=[("MusicXML Files", "*.musicxml *.xml *.mxl")]
        ) 
        if file_path:
            # Reset the app before loading a new file
            self.reset_app()

            # Update the file path entry
            self.entry_file_path.delete(0, tk.END)
            self.entry_file_path.insert(0, file_path)

            # Load parts from the new MusicXML file
            self.load_parts_from_musicxml(file_path)                


    def save_musicxml(self):
        """Save the modified MusicXML file."""
        logging.info(f"Using Work Directory: {WORK_DIRECTORY}")
        file_path = filedialog.asksaveasfilename(
            initialdir=WORK_DIRECTORY,  # Use the work directory
            defaultextension=".musicxml",
            filetypes=[("MusicXML Files", "*.musicxml")]
        )
        if file_path:
            # Pretty-print the XML tree
            self.pretty_print_xml(self.musicxml_root)

            # Write the XML to the file
            self.musicxml_tree.write(file_path, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Success", f"File saved as {file_path}")

            # Store the saved file path for launching the external application
            self.saved_file_path = file_path 


            
    def populate_listbox(self):
        """Populate the listbox with instruments from XML."""
        self.instruments_with_details.clear()
        self.instrument_listbox.delete(0, tk.END)
        for instrument in self.instruments_xml.findall(".//Instrument"):
            instrument_id = instrument.attrib.get("id")
            long_name = instrument.find("longName").text if instrument.find("longName") is not None else "Unknown"
            short_name = instrument.find("shortName").text if instrument.find("shortName") is not None else ""
            music_xml_id = instrument.find("musicXMLid").text if instrument.find("musicXMLid") is not None else ""
            transposition_element = instrument.find(".//traitName[@type='transposition']")
            transposition = transposition_element.text if transposition_element is not None else ""
            transpose_diatonic = instrument.find("transposeDiatonic").text if instrument.find("transposeDiatonic") is not None else ""
            transpose_chromatic = instrument.find("transposeChromatic").text if instrument.find("transposeChromatic") is not None else ""
            transpose_octave = instrument.find("transposeOctaveChange").text if instrument.find("transposeOctaveChange") is not None else ""

            display_text = f"{long_name} {transposition}".strip()
            self.instruments_with_details.append({
                "id": instrument_id,
                "longName": long_name,
                "shortName": short_name,
                "musicXMLid": music_xml_id,
                "transposition": transposition,
                "transposeDiatonic": transpose_diatonic,
                "transposeChromatic": transpose_chromatic,
                "transposeOctaveChange": transpose_octave
            })
            self.instrument_listbox.insert(tk.END, display_text)
        self.filtered_instruments = self.instruments_with_details.copy()
 

    def show_instrument_details(self, event):
        """Show detailed information of the selected instrument."""
        selected_index = self.instrument_listbox.curselection()
        if selected_index:
            selected_index = selected_index[0]
            if selected_index < len(self.filtered_instruments):
                selected_instrument = self.filtered_instruments[selected_index]

                # Clear previous details
                self.detail_text.delete(1.0, tk.END)

                # Iterate over all 'Instrument' elements in XML
                for instrument in self.instruments_xml.findall('.//Instrument'):
                    instrument_id_xml = instrument.attrib.get('id', '').strip()

                    # Check if the selected instrument matches
                    if instrument_id_xml == selected_instrument['id']:
                        self.detail_text.insert(tk.END, f"ID: {instrument_id_xml}\n")

                        long_name_element = instrument.find('longName')
                        long_name = long_name_element.text if long_name_element is not None else "Unknown name"
                        self.detail_text.insert(tk.END, f"Long Name: {long_name}\n")

                        track_name_element = instrument.find('trackName')
                        track_name = track_name_element.text if track_name_element is not None else "No track name"
                        self.detail_text.insert(tk.END, f"Track Name: {track_name}\n")

                        short_name_element = instrument.find('shortName')
                        short_name = short_name_element.text if short_name_element is not None else "No short name"
                        self.detail_text.insert(tk.END, f"Short Name: {short_name}\n")

                        description_element = instrument.find('description')
                        description = description_element.text if description_element is not None else "No description"
                        self.detail_text.insert(tk.END, f"Description: {description}\n")

                        music_xml_id_element = instrument.find('musicXMLid')
                        music_xml_id = music_xml_id_element.text if music_xml_id_element is not None else "No MusicXML ID"
                        self.detail_text.insert(tk.END, f"MusicXML ID: {music_xml_id}\n")

                        clef_element = instrument.find('clef')
                        clef = clef_element.text if clef_element is not None else "No clef"
                        self.detail_text.insert(tk.END, f"Clef: {clef}\n")

                        barline_span_element = instrument.find('barlineSpan')
                        barline_span = barline_span_element.text if barline_span_element is not None else "No barline span"
                        self.detail_text.insert(tk.END, f"Barline Span: {barline_span}\n")

                        a_pitch_range_element = instrument.find('aPitchRange')
                        a_pitch_range = a_pitch_range_element.text if a_pitch_range_element is not None else "No pitch range"
                        self.detail_text.insert(tk.END, f"A Pitch Range: {a_pitch_range}\n")

                        p_pitch_range_element = instrument.find('pPitchRange')
                        p_pitch_range = p_pitch_range_element.text if p_pitch_range_element is not None else "No pitch range"
                        self.detail_text.insert(tk.END, f"P Pitch Range: {p_pitch_range}\n")

                        transpose_diatonic_element = instrument.find('transposeDiatonic')
                        transpose_diatonic = transpose_diatonic_element.text if transpose_diatonic_element is not None else "No diatonic transposition"
                        self.detail_text.insert(tk.END, f"Transpose Diatonic: {transpose_diatonic}\n")

                        transpose_chromatic_element = instrument.find('transposeChromatic')
                        transpose_chromatic = transpose_chromatic_element.text if transpose_chromatic_element is not None else "No chromatic transposition"
                        self.detail_text.insert(tk.END, f"Transpose Chromatic: {transpose_chromatic}\n")

                        channel_element = instrument.find('Channel')
                        if channel_element is not None:
                            program_element = channel_element.find('program')
                            if program_element is not None:
                                program_value = program_element.get('value', 'No program value')
                                self.detail_text.insert(tk.END, f"MIDI Program: {program_value}\n")
                            else:
                                self.detail_text.insert(tk.END, "No MIDI program found\n")
                        else:
                            self.detail_text.insert(tk.END, "No MIDI channel found\n")

                        break  # Stop after finding the first match

    def filter_instruments(self, event):
        """Filter the listbox based on the search term."""
        search_term = self.search_box.get().lower()
        self.instrument_listbox.delete(0, tk.END)
        self.filtered_instruments = []  # Reset the filtered list

        for instrument in self.instruments_with_details:
            if search_term in instrument['longName'].lower():
                display_text = f"{instrument['longName']} {instrument['transposition']}".strip()
                self.instrument_listbox.insert(tk.END, display_text)
                self.filtered_instruments.append(instrument)  # Track filtered instruments properly


    def skip_mapping(self):
        """Skip the current part and move to the next one."""
        if self.current_part_index < len(self.parts) - 1:
            self.current_part_index += 1  # Move to the next part
            self.show_next_part()  # Display the next part
        else:
            messagebox.showinfo("Info", "No more parts to process.")
     
        def skip_mapping(self):
            """Skip the current mapping."""
            messagebox.showinfo("Info", "Mapping skipped!")
        print(f"Current part index: {self.current_part_index}")
        print(f"Total parts: {len(self.parts)}")    



    def load_parts_from_musicxml(self, file_path):
        """Extract parts from the MusicXML file and prepare them for editing."""
        try:
            # Check if the file is an .mxl file
            if file_path.lower().endswith('.mxl'):
                # Extract the .mxl file and get the path to the main MusicXML file
                file_path = self.extract_mxl(file_path)
            
            # Parse the MusicXML file
            self.musicxml_tree = ET.parse(file_path)
            self.musicxml_root = self.musicxml_tree.getroot()
        except Exception as e:
            print(f"Error parsing MusicXML file: {e}")  # Print error if the file is invalid
            messagebox.showerror("Error", f"Failed to read MusicXML file: {e}")
            logging.error(f"Failed to read MusicXML file: {e}")  # Fix: Use logging.error instead of logging.info
            return

        print("MusicXML parsed successfully.")  # Debugging: Ensure file is parsed
        logging.info("MusicXML parsed successfully.") 
        
        self.parts = []  # Clear previous parts

        for score_part in self.musicxml_root.findall(".//score-part"):
            part_name = score_part.find("part-name").text if score_part.find("part-name") is not None else "Unknown Part"
            instrument_name = score_part.find("score-instrument/instrument-name")
            instrument_name = instrument_name.text if instrument_name is not None else "Unknown Instrument"
            part_id = score_part.get("id")  # Get unique ID

            self.parts.append({
                "id": part_id,
                "name": part_name,
                "instrument": instrument_name
            })

        print(f"Loaded {len(self.parts)} parts.")  # Debug: Check if parts are found
        logging.info(f"Loaded {len(self.parts)} parts.") 

        if self.parts:
            self.label.config(text="Parts loaded. Click 'Start' to begin.")  # Update UI            

  

    def reset_app(self):
        """Reset the application to its initial state."""
        # Clear the parts list and reset the index
        self.parts = []
        self.current_part_index = 0

        # Re-enable the "Start part mapping" button
        self.start_button.config(state=tk.NORMAL)

        # Clear the part name label
        self.label.config(text="Mapping instrument for: ")

        # Clear the instrument listbox and details
        self.instrument_listbox.delete(0, tk.END)
        self.detail_text.delete(1.0, tk.END)

        # Clear the file path entry
        self.entry_file_path.delete(0, tk.END)

        # Clear the search box
        self.search_box.delete(0, tk.END)

        # Repopulate the listbox with instruments
        self.populate_listbox()

        # Log the reset
        logging.info("Application reset for new file.")



    def start_mapping(self):
        """Begin the instrument mapping process."""
        print(f"Start button clicked. Parts loaded: {len(self.parts)}")  # Debugging

        if not self.parts:
            messagebox.showerror("Error", "No parts loaded. Please select a MusicXML file first.")
            logging.info("Error", "No parts loaded. Please select a MusicXML file first.")
            return

        self.start_button.config(state=tk.DISABLED)  # Disable start button once started
        self.show_next_part()  # Begin processing

    def show_next_part(self):
        """Show the next part for mapping."""
        if self.current_part_index >= len(self.parts):
            messagebox.showinfo("Done", "All parts have been processed.")
            logging.info("All parts have been processed.")
            return

        part = self.parts[self.current_part_index]

        # Directly set the part name in the label (no need for `self.part_name_var`)
        self.label.config(text=f"Mapping instrument for: {part['name']}")
        self.part_name = part["name"]  # Store the current part name
        logging.info(f"Mapping instrument for: {part['name']}")

        # Find and highlight the instrument in the list (if present)
        for index, instrument in enumerate(self.filtered_instruments):
            if instrument["longName"] == part["instrument"]:
                self.instrument_listbox.selection_clear(0, tk.END)
                self.instrument_listbox.selection_set(index)
                self.instrument_listbox.activate(index)
                self.instrument_listbox.see(index)
                self.show_instrument_details(None)
                break

    def save_mappings(self):
        """Save the selected instrument to the MusicXML file and move to the next part."""
        selected_index = self.instrument_listbox.curselection()
        if not selected_index:
            tk.messagebox.showwarning("Warning", "Please select an instrument.")
            return

        selected_index = selected_index[0]
        selected_instrument = self.filtered_instruments[selected_index]

        # Get the current part's name properly
        part = self.parts[self.current_part_index]
        part_name = part["name"]

        logging.debug(f"User selected {selected_instrument['longName']} for {part_name}")

        # Apply the selection to the MusicXML file
        new_part_name = selected_instrument["longName"]
        new_part_abbreviation = selected_instrument.get("shortName", new_part_name)  # Default to short name
        new_transposition_diatonic = selected_instrument.get("transposeDiatonic", 0)  # Default 0 if missing
        new_transposition_chromatic = selected_instrument.get("transposeChromatic", 0)  # Default 0 if missing
        new_transposition_octave = selected_instrument.get("transposeOctaveChange", 0)  # Default 0 if missing
        new_instrument_sound = selected_instrument.get("musicXMLid", "")  # If missing, leave empty!

        # Update the MusicXML structure
        for score_part in self.musicxml_root.findall(".//score-part"):
            if score_part.get("id") == part["id"]:
                # Update Part Name
                part_name_elem = score_part.find("part-name")
                if part_name_elem is None:
                    part_name_elem = ET.SubElement(score_part, "part-name")
                part_name_elem.text = new_part_name

                # Update Part Abbreviation
                part_abbr_elem = score_part.find("part-abbreviation")
                if part_abbr_elem is None:
                    part_abbr_elem = ET.SubElement(score_part, "part-abbreviation")

                new_short_name = selected_instrument.get("shortName", new_part_name)
                part_abbr_elem.text = new_short_name
                logging.info(f"New part abbreviation set: {new_short_name}")



               
                # Update Instrument Name inside <score-instrument>
                instr_elem = score_part.find("score-instrument")
                if instr_elem is not None:
                    instr_name_elem = instr_elem.find("instrument-name")
                    if instr_name_elem is None:
                        instr_name_elem = ET.SubElement(instr_elem, "instrument-name")
                    instr_name_elem.text = new_part_name



                # Update Instrument Sound (Fix)
                instr_sound_elem = instr_elem.find("instrument-sound")
                if instr_sound_elem is None:
                    instr_sound_elem = ET.SubElement(instr_elem, "instrument-sound")

                # Get correct MusicXML ID (do not default to empty if it exists)
                new_instrument_sound = selected_instrument.get("musicXMLid", "").strip()

                if new_instrument_sound:
                    instr_sound_elem.text = new_instrument_sound
                    logging.info(f"Updated instrument sound: '{new_instrument_sound}'")
                else:
                    logging.warning(f"No MusicXML ID found for {new_part_name}, leaving <instrument-sound> unchanged")

         # Find the part first
        part_elem = self.musicxml_root.find(f".//part[@id='{part['id']}']")
        if part_elem is not None:
            measure_elem = part_elem.find("measure/attributes")
            if measure_elem is not None:
                # Find or create the <transpose> element
                transpose_elem = measure_elem.find("transpose")
                if transpose_elem is None:
                    transpose_elem = ET.SubElement(measure_elem, "transpose")  # Create if missing

                # Assign correct transposition values
                diatonic_value = selected_instrument.get("transposeDiatonic")
                chromatic_value = selected_instrument.get("transposeChromatic")
                octave_value = selected_instrument.get("transposeOctaveChange")

                if diatonic_value is not None:
                    diatonic_elem = transpose_elem.find("diatonic")
                    if diatonic_elem is None:
                        diatonic_elem = ET.SubElement(transpose_elem, "diatonic")
                    diatonic_elem.text = str(diatonic_value)

                if chromatic_value is not None:
                    chromatic_elem = transpose_elem.find("chromatic")
                    if chromatic_elem is None:
                        chromatic_elem = ET.SubElement(transpose_elem, "chromatic")
                    chromatic_elem.text = str(chromatic_value)

                if octave_value is not None:
                    octave_change_elem = transpose_elem.find("octave-change")
                    if octave_change_elem is None:
                        octave_change_elem = ET.SubElement(transpose_elem, "octave-change")
                    octave_change_elem.text = str(octave_value)

                logging.info(f"Updated transposition for {new_part_name}: "
                             f"Diatonic={diatonic_value}, Chromatic={chromatic_value}, Octave={octave_value}")

        print(f"Selected Instrument: {selected_instrument}")
        print(f"Short Name: {selected_instrument.get('shortName')}")
        print(f"MusicXML ID: {selected_instrument.get('musicXMLid')}")
        print(f"Transposition Values: Diatonic={selected_instrument.get('transposeDiatonic')}, Chromatic={selected_instrument.get('transposeChromatic')}, Octave={selected_instrument.get('transposeOctaveChange')}")

        # Move to the next part
        self.current_part_index += 1
        self.show_next_part()

    def pretty_print_xml(self, element, indent="  ", level=0):
        """
        Pretty-print an XML element with indentation and line breaks.
        """
        # Add indentation
        indent_str = indent * level
        if len(element):  # If the element has children
            # Add a newline and indentation after the opening tag
            if not element.text or not element.text.strip():
                element.text = "\n" + indent_str + indent
            # Recursively pretty-print each child
            for child in element:
                self.pretty_print_xml(child, indent, level + 1)
            # Add a newline and indentation before the closing tag
            if not child.tail or not child.tail.strip():
                child.tail = "\n" + indent_str
        else:  # If the element has no children
            # Add a newline and indentation after the opening tag
            if not element.text or not element.text.strip():
                element.text = "\n" + indent_str + indent
            # Add a newline and indentation before the closing tag
            if not element.tail or not element.tail.strip():
                element.tail = "\n" + indent_str

    def launch_app(self):
        """Launch the external application (e.g., MuseScore) with the saved file."""
        if not hasattr(self, 'saved_file_path') or not self.saved_file_path:
            messagebox.showwarning("Warning", "No file has been saved yet. Please save the file first.")
            return

        try:
            # Launch the external application with the saved file as an argument (non-blocking)
            subprocess.Popen([external_app, self.saved_file_path])
        except FileNotFoundError:
            messagebox.showerror("Error", f"{EXT_APPLICATION} not found. Please check the path: {external_app}")
            logging.error(f"{EXT_APPLICATION} not found at {external_app}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {EXT_APPLICATION}: {e}")
            logging.error(f"Failed to launch {EXT_APPLICATION}: {e}")

 

def main():
    # Step 1: Set up argument parsing
    parser = argparse.ArgumentParser(description="Open and process a file.")
    parser.add_argument('file', type=str, nargs='?', help="The path to the file to be opened (optional).")
    
    # Step 2: Parse the arguments
    args = parser.parse_args()
    
    # Step 3: Create the main application window
    root = tk.Tk()

    # Step 4: Initialize the InstrumentMapper
    app = InstrumentMapper(root, args.file)

    # Step 5: If a file is provided via command line, populate the entry widget and load parts
    if args.file and os.path.isfile(args.file):
        app.entry_file_path.delete(0, tk.END)
        app.entry_file_path.insert(0, args.file)
        app.load_parts_from_musicxml(args.file)  # Load parts from the specified file

    # Start the main event loop
    root.mainloop()

    
if __name__ == "__main__":
    main()    

### END 

