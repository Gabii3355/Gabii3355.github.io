from pymol import cmd

def mutate_ssdna(selection, new_base):
    base_map = {
        'A': 'Adenine',
        'C': 'Cytosine',
        'G': 'Guanine',
        'T': 'Thymine'
    }
    
    new_base = new_base.upper()
    if new_base not in base_map:
        print(f"Error: Unknown base '{new_base}'. Use A, C, G, T.")
        return

    mode_name = base_map[new_base]

    try:
        cmd.wizard("nucmutagenesis")
        cmd.refresh_wizard()
        cmd.get_wizard().do_select(selection)
        cmd.get_wizard().set_mode(mode_name)
        cmd.get_wizard().apply()
        cmd.wizard() 
        # KLUCZOWE: Wymuszenie na silniku PyMOLa przeliczenia nowej topologii
        cmd.sort()
        print(f"Success: Mutated {selection} on {mode_name}.")
    except Exception as e:
        print(f"Error appear: {e}\nMake sure you are using PyMOL version 2.2 or later.")

cmd.extend("mutate_ssdna", mutate_ssdna)
